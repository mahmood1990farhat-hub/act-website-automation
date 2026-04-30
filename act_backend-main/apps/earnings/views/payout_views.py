from rest_framework.response import Response
from rest_framework import status
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsVerifiedAndProfileCompleted, IsNormalDriver
from django.db import transaction
from django.db.models import Sum, Count
from django.db import IntegrityError
from apps.earnings.models import DriverEarningLedger, WithdrawalRequest
from utils.common import get_locale
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
import logging

logger = logging.getLogger(__name__)


class DriverPayoutRequestView(EMADBaseView):
    """
    Driver submits a withdrawal request.
    Creates WithdrawalRequest record but does NOT change earnings status.
    Earnings remain AVAILABLE until admin processes payout.
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        driver = request.user.base_driver
        if not driver:
            message = get_bilingual_error_message(
                'Driver profile not found',
                'ملف السائق غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Get optional note from request
        note = request.data.get('note', '').strip() if hasattr(request, 'data') else ''
        
        # One active request per driver: SUBMITTED or APPROVED (until admin decision + payout)
        ACTIVE_STATUSES = ['SUBMITTED', 'APPROVED']
        
        # Calculate available balance and create request inside one transaction with lock
        with transaction.atomic():
            # Lock: prevent concurrent requests; enforce one active request per driver
            existing_active = WithdrawalRequest.objects.filter(
                driver=driver,
                status__in=ACTIVE_STATUSES
            ).select_for_update().first()
            if existing_active:
                message = get_bilingual_error_message(
                    'You already have a payout request pending. Wait for admin decision before submitting again.',
                    'لديك بالفعل طلب سحب قيد الانتظار. انتظر قرار الإدارة قبل التقديم مرة أخرى.',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            available_earnings = DriverEarningLedger.objects.filter(
                driver=driver,
                status='AVAILABLE',
                stripe_transfer_id__isnull=True  # Not already paid
            )
            
            # Calculate total available amount
            balance_result = available_earnings.aggregate(
                total=Sum('net_amount'),
                count=Count('id')
            )
            
            available_balance = balance_result['total'] or 0
            earnings_count = balance_result['count'] or 0
            
            if available_balance == 0 or earnings_count == 0:
                message = get_bilingual_error_message(
                    'No available earnings for payout',
                    'لا توجد أرباح متاحة للدفع',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Get currency from first earning (all should be same currency)
            first_earning = available_earnings.first()
            currency = first_earning.currency if first_earning else 'GBP'
            
            # Create withdrawal request (DB constraint unique_driver_active_request enforces one active per driver)
            try:
                withdrawal_request = WithdrawalRequest.objects.create(
                    driver=driver,
                    status='SUBMITTED',
                    requested_amount=None,  # Always NULL - pay all available
                    currency=currency,
                    note=note
                )
            except IntegrityError:
                message = get_bilingual_error_message(
                    'You already have a payout request pending. Wait for admin decision before submitting again.',
                    'لديك بالفعل طلب سحب قيد الانتظار. انتظر قرار الإدارة قبل التقديم مرة أخرى.',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Withdrawal request created for driver {driver.id}: request_id={withdrawal_request.id}, "
                       f"available_balance={available_balance}, earnings_count={earnings_count}")
        
        message = get_bilingual_error_message(
            'Withdrawal request submitted successfully. Awaiting admin approval.',
            'تم تقديم طلب السحب بنجاح. في انتظار موافقة الإدارة.',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": {
                "request_id": str(withdrawal_request.id),
                "available_balance": float(available_balance),
                "earnings_count": earnings_count,
                "currency": currency,
                "status": withdrawal_request.status
            }
        }, status=status.HTTP_200_OK)
