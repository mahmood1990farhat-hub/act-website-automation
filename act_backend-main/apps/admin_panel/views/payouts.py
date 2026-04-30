"""
Admin payouts to drivers.

- If driver has stripe_account_id (completed Stripe Connect): we use stripe.Transfer.create
  to send money from the platform to their Connect account; Stripe holds their bank details.
- If driver has no Stripe Connect but has bank_details (onboarding): we mark as PAID and
  record stripe_transfer_id='manual'; admin pays the driver's bank account manually.
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from utils.EMDBase import EMADBaseView
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.earnings.models import DriverEarningLedger, PayoutBatch, WithdrawalRequest
from utils.common import get_locale
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
import stripe
from django.conf import settings
import uuid
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class AdminBulkPayoutView(EMADBaseView):
    """
    Admin bulk payout with two modes:
    - Mode A: Pay approved withdrawal requests (pay all available earnings for those drivers)
    - Mode B: Pay all available earnings (weekly payout, existing behavior)
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get mode from request
        mode = request.data.get('mode', 'all_available').lower() if hasattr(request, 'data') else 'all_available'
        request_ids = request.data.get('request_ids', []) if hasattr(request, 'data') else []
        driver_id = request.data.get('driver_id', None) if hasattr(request, 'data') else None
        
        # MODE A: Pay approved withdrawal requests
        if mode == 'approved_requests':
            return self._process_approved_requests(request, locale, request_ids, driver_id)
        
        # MODE B: Pay all available earnings (existing behavior)
        elif mode == 'all_available':
            return self._process_all_available(request, locale)
        
        else:
            message = get_bilingual_error_message(
                f'Invalid mode: {mode}. Use "approved_requests" or "all_available"',
                f'وضع غير صالح: {mode}. استخدم "approved_requests" أو "all_available"',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
    
    def _process_approved_requests(self, request, locale, request_ids, driver_id):
        """
        Mode A: Process approved withdrawal requests
        Pay all AVAILABLE earnings for drivers with approved requests
        """
        with transaction.atomic():
            # Get approved withdrawal requests
            approved_requests_query = WithdrawalRequest.objects.select_for_update().filter(
                status='APPROVED'
            ).select_related('driver__user')
            
            # Filter by request_ids if provided
            if request_ids:
                try:
                    # Convert string UUIDs to UUID objects
                    from uuid import UUID
                    uuid_list = [UUID(rid) for rid in request_ids]
                    approved_requests_query = approved_requests_query.filter(id__in=uuid_list)
                except (ValueError, TypeError) as e:
                    message = get_bilingual_error_message(
                        'Invalid request_ids format',
                        'تنسيق معرفات الطلبات غير صالح',
                        locale
                    )
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Filter by driver_id if provided
            if driver_id:
                try:
                    approved_requests_query = approved_requests_query.filter(driver_id=int(driver_id))
                except ValueError:
                    message = get_bilingual_error_message(
                        'Invalid driver_id',
                        'معرف السائق غير صالح',
                        locale
                    )
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            approved_requests = list(approved_requests_query)
            
            if not approved_requests:
                message = get_bilingual_error_message(
                    'No approved withdrawal requests found',
                    'لا توجد طلبات سحب معتمدة',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Collect all drivers from approved requests
            driver_ids = [req.driver.id for req in approved_requests]
            
            # Get all AVAILABLE earnings for these drivers.
            # Do NOT select_related('driver__bank_details') here: nullable FK causes an outer join,
            # and PostgreSQL does not allow FOR UPDATE on the nullable side of an outer join.
            available_earnings = DriverEarningLedger.objects.select_for_update().filter(
                driver_id__in=driver_ids,
                status='AVAILABLE',
                stripe_transfer_id__isnull=True  # Not already paid
            ).select_related('driver', 'trip')
            
            earnings_list = list(available_earnings)
            
            if not earnings_list:
                message = get_bilingual_error_message(
                    'No available earnings found for approved requests',
                    'لا توجد أرباح متاحة للطلبات المعتمدة',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            total_amount = sum(e.net_amount for e in earnings_list)
            currency = earnings_list[0].currency if earnings_list else 'GBP'
            
            # Create payout batch
            batch_id = str(uuid.uuid4())
            batch = PayoutBatch.objects.create(
                batch_id=batch_id,
                status='PENDING',
                total_amount=total_amount,
                currency=currency,
                total_earnings=len(earnings_list),
                created_by=request.user
            )
            
            # Mark earnings as LOCKED
            DriverEarningLedger.objects.filter(
                id__in=[e.id for e in earnings_list]
            ).update(status='LOCKED', payout_batch=batch)
            
            # Track which requests will be paid (for later status update)
            requests_by_driver = {req.driver.id: req for req in approved_requests}
        
        # Process each earning (same logic as Mode B)
        results = []
        successful = 0
        failed = 0
        skipped = 0
        errors = []
        drivers_paid = set()  # Track which drivers were successfully paid
        
        for earning in earnings_list:
            driver = earning.driver
            
            # No Stripe Connect: use manual payout if driver has bank details (from onboarding)
            if not driver.stripe_account_id:
                if getattr(driver, 'bank_details_id', None) and driver.bank_details:
                    # Manual payout: admin will transfer to driver's bank account (account_number + sort_code)
                    earning.status = 'PAID'
                    earning.stripe_transfer_id = 'manual'  # Sentinel: paid via bank transfer, not Stripe
                    earning.paid_at = timezone.now()
                    earning.save()
                    successful += 1
                    drivers_paid.add(driver.id)
                    results.append({
                        "driver_id": driver.id,
                        "earning_id": earning.id,
                        "status": "paid_manual",
                        "reason": "Manual bank transfer – pay driver's bank account (see withdrawal-requests for details)",
                        "amount": float(earning.net_amount),
                        "currency": earning.currency,
                    })
                else:
                    skipped += 1
                    results.append({
                        "driver_id": driver.id,
                        "earning_id": earning.id,
                        "status": "skipped",
                        "reason": "No Stripe account and no bank details – add bank details in onboarding or connect Stripe"
                    })
                    earning.status = 'AVAILABLE'
                    earning.payout_batch = None
                    earning.save()
                continue

            try:
                # --- Stripe Transfer: platform sends earnings to driver's Connect account ---
                # Money moves from platform Stripe balance to the connected account (Express).
                # Stripe then pays out to the driver's bank (added during Connect onboarding).
                # We do NOT use driver's stored bank_details here; Stripe holds bank info for Connect.
                idempotency_key = f"transfer_{earning.id}_{batch_id}"
                transfer = stripe.Transfer.create(
                    amount=int(earning.net_amount * 100),
                    currency=earning.currency.lower(),
                    destination=driver.stripe_account_id,
                    metadata={
                        "trip_id": earning.trip.id,
                        "earning_id": earning.id,
                        "batch_id": batch_id
                    },
                    idempotency_key=idempotency_key
                )

                earning.status = 'PAID'
                earning.stripe_transfer_id = transfer.id
                earning.stripe_idempotency_key = idempotency_key
                earning.paid_at = timezone.now()
                earning.save()

                successful += 1
                drivers_paid.add(driver.id)
                results.append({
                    "driver_id": driver.id,
                    "earning_id": earning.id,
                    "status": "paid",
                    "transfer_id": transfer.id
                })
            except stripe.error.StripeError as e:
                # Revert to AVAILABLE
                earning.status = 'AVAILABLE'
                earning.payout_batch = None
                earning.save()
                
                failed += 1
                error_msg = str(e)
                errors.append({
                    "earning_id": earning.id,
                    "driver_id": driver.id,
                    "error": error_msg
                })
                results.append({
                    "driver_id": driver.id,
                    "earning_id": earning.id,
                    "status": "failed",
                    "error": error_msg
                })
        
        # Update batch status
        batch.successful_transfers = successful
        batch.failed_transfers = failed
        batch.error_log = errors if errors else None
        
        if failed == 0:
            batch.status = 'COMPLETED'
        elif successful == 0:
            batch.status = 'FAILED'
        else:
            batch.status = 'PARTIAL'
        
        batch.completed_at = timezone.now()
        batch.save()
        
        # Update withdrawal request statuses
        # Only mark as PAID if ALL earnings for that driver were successfully paid
        with transaction.atomic():
            for driver_id_paid in drivers_paid:
                if driver_id_paid in requests_by_driver:
                    withdrawal_request = requests_by_driver[driver_id_paid]
                    # Check if all earnings for this driver were paid
                    driver_earnings_in_batch = [e for e in earnings_list if e.driver.id == driver_id_paid]
                    driver_successful = [e for e in driver_earnings_in_batch if e.status == 'PAID']
                    
                    if len(driver_successful) == len(driver_earnings_in_batch):
                        # All earnings paid, mark request as PAID
                        withdrawal_request.status = 'PAID'
                        withdrawal_request.payout_batch = batch
                        withdrawal_request.save(update_fields=['status', 'payout_batch'])
        
        return Response({
            "success": True,
            "data": {
                "batch_id": batch_id,
                "status": batch.status,
                "mode": "approved_requests",
                "total_earnings": len(earnings_list),
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "results": results
            }
        }, status=status.HTTP_200_OK)
    
    def _process_all_available(self, request, locale):
        """
        Mode B: Process all available earnings (existing behavior)
        """
        # Lock AVAILABLE earnings to prevent race conditions and calculate totals
        with transaction.atomic():
            # Do NOT select_related('driver__bank_details') with select_for_update: nullable FK
            # causes an outer join; PostgreSQL forbids FOR UPDATE on the nullable side.
            available_earnings = DriverEarningLedger.objects.select_for_update().filter(
                status='AVAILABLE',
                stripe_transfer_id__isnull=True  # Not already paid
            ).select_related('driver', 'trip')
            
            # Get earnings list and calculate totals
            earnings_list = list(available_earnings)
            
            # Check if there are any earnings to process
            if not earnings_list:
                message = get_bilingual_error_message(
                    'No available earnings to process for payout.',
                    'لا توجد أرباح متاحة للمعالجة للدفع.',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            total_amount = sum(e.net_amount for e in earnings_list)
            currency = earnings_list[0].currency if earnings_list else 'GBP'
            
            # Create payout batch with calculated values
            batch_id = str(uuid.uuid4())
            batch = PayoutBatch.objects.create(
                batch_id=batch_id,
                status='PENDING',
                total_amount=total_amount,
                currency=currency,
                total_earnings=len(earnings_list),
                created_by=request.user
            )
            
            # Mark earnings as LOCKED
            DriverEarningLedger.objects.filter(
                id__in=[e.id for e in earnings_list]
            ).update(status='LOCKED', payout_batch=batch)
        
        # Process each earning
        results = []
        successful = 0
        failed = 0
        skipped = 0
        errors = []
        
        for earning in earnings_list:
            driver = earning.driver
            
            # No Stripe Connect: use manual payout if driver has bank details (from onboarding)
            if not driver.stripe_account_id:
                if getattr(driver, 'bank_details_id', None) and driver.bank_details:
                    earning.status = 'PAID'
                    earning.stripe_transfer_id = 'manual'
                    earning.paid_at = timezone.now()
                    earning.save()
                    successful += 1
                    results.append({
                        "driver_id": driver.id,
                        "earning_id": earning.id,
                        "status": "paid_manual",
                        "reason": "Manual bank transfer – pay driver's bank account",
                        "amount": float(earning.net_amount),
                        "currency": earning.currency,
                    })
                else:
                    skipped += 1
                    results.append({
                        "driver_id": driver.id,
                        "earning_id": earning.id,
                        "status": "skipped",
                        "reason": "No Stripe account and no bank details"
                    })
                    earning.status = 'AVAILABLE'
                    earning.payout_batch = None
                    earning.save()
                continue
            
            try:
                # --- Stripe Transfer: platform → driver Connect account ---
                # Same as in approved_requests mode; driver must have completed Connect onboarding.
                idempotency_key = f"transfer_{earning.id}_{batch_id}"
                transfer = stripe.Transfer.create(
                    amount=int(earning.net_amount * 100),
                    currency=earning.currency.lower(),
                    destination=driver.stripe_account_id,
                    metadata={
                        "trip_id": earning.trip.id,
                        "earning_id": earning.id,
                        "batch_id": batch_id
                    },
                    idempotency_key=idempotency_key
                )

                earning.status = 'PAID'
                earning.stripe_transfer_id = transfer.id
                earning.stripe_idempotency_key = idempotency_key
                earning.paid_at = timezone.now()
                earning.save()

                successful += 1
                results.append({
                    "driver_id": driver.id,
                    "earning_id": earning.id,
                    "status": "paid",
                    "transfer_id": transfer.id
                })
            except stripe.error.StripeError as e:
                earning.status = 'AVAILABLE'
                earning.payout_batch = None
                earning.save()

                failed += 1
                error_msg = str(e)
                errors.append({
                    "earning_id": earning.id,
                    "driver_id": driver.id,
                    "error": error_msg
                })
                results.append({
                    "driver_id": driver.id,
                    "earning_id": earning.id,
                    "status": "failed",
                    "error": error_msg
                })

        # Update batch status
        batch.successful_transfers = successful
        batch.failed_transfers = failed
        batch.error_log = errors if errors else None

        # Determine batch status: account for skipped earnings
        total_processed = successful + failed + skipped
        if successful == total_processed and total_processed > 0:
            batch.status = 'COMPLETED'
        elif successful == 0 and (failed > 0 or skipped > 0):
            # All failed or skipped
            batch.status = 'FAILED'
        elif successful > 0 and (failed > 0 or skipped > 0):
            # Some succeeded, some failed/skipped
            batch.status = 'PARTIAL'
        else:
            # No earnings processed (shouldn't happen, but safety check)
            batch.status = 'FAILED'
        
        batch.completed_at = timezone.now()
        batch.save()
        
        return Response({
            "success": True,
            "data": {
                "batch_id": batch_id,
                "status": batch.status,
                "mode": "all_available",
                "total_earnings": len(earnings_list),
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "results": results
            }
        }, status=status.HTTP_200_OK)

