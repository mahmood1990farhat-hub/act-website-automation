from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from utils.EMDBase import EMADBaseView
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, Count
from apps.earnings.models import WithdrawalRequest, DriverEarningLedger
from utils.common import get_locale
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)


class WithdrawalRequestListView(EMADBaseView):
    """
    List all withdrawal requests with filters
    GET /api/admin-panel/withdrawal-requests/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get query parameters
        status_filter = request.query_params.get('status', None)
        driver_id = request.query_params.get('driver_id', None)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Build query (include driver bank_details for manual payout)
        requests_query = WithdrawalRequest.objects.select_related(
            'driver__user',
            'driver__bank_details',
            'reviewed_by',
            'payout_batch'
        ).all()
        
        if status_filter:
            requests_query = requests_query.filter(status=status_filter.upper())
        
        if driver_id:
            try:
                requests_query = requests_query.filter(driver_id=int(driver_id))
            except ValueError:
                message = get_bilingual_error_message(
                    'Invalid driver ID',
                    'معرف السائق غير صالح',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Get total count
        total_count = requests_query.count()
        
        # Apply pagination
        withdrawal_requests = requests_query.order_by('-created_at')[offset:offset + page_size]
        
        # Serialize requests
        requests_data = []
        for req in withdrawal_requests:
            # Calculate current available balance for this driver
            available_balance = DriverEarningLedger.objects.filter(
                driver=req.driver,
                status='AVAILABLE',
                stripe_transfer_id__isnull=True
            ).aggregate(total=Sum('net_amount'))['total'] or 0
            
            # Bank details (from onboarding) – for manual payout when driver has no Stripe
            bank_details = None
            if getattr(req.driver, 'bank_details', None):
                b = req.driver.bank_details
                bank_details = {
                    'account_number': b.bank_account_number,
                    'sort_code': b.sort_code,
                    'registered_address': b.registered_address,
                }
            requests_data.append({
                'id': str(req.id),
                'driver': {
                    'id': req.driver.id,
                    'name': f"{req.driver.user.first_name} {req.driver.user.last_name}".strip(),
                    'email': req.driver.user.email,
                    'phone': req.driver.user.phone_number,
                    'bank_details': bank_details,
                },
                'status': req.status,
                'requested_amount': float(req.requested_amount) if req.requested_amount else None,
                'currency': req.currency,
                'note': req.note,
                'reviewed_by': {
                    'id': req.reviewed_by.id,
                    'email': req.reviewed_by.email,
                } if req.reviewed_by else None,
                'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
                'admin_note': req.admin_note,
                'payout_batch_id': req.payout_batch.batch_id if req.payout_batch else None,
                'created_at': req.created_at.isoformat(),
                'updated_at': req.updated_at.isoformat(),
                'current_available_balance': float(available_balance),  # Current balance at time of viewing
            })
        
        return Response({
            "success": True,
            "data": {
                "requests": requests_data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
                    "has_next": offset + page_size < total_count,
                    "has_previous": page > 1,
                }
            }
        }, status=status.HTTP_200_OK)


class ApproveWithdrawalRequestView(EMADBaseView):
    """
    Approve a withdrawal request
    POST /api/admin-panel/withdrawal-requests/<request_id>/approve/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['post']
    
    def handle_post(self, request, request_id):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get admin note from request
        admin_note = request.data.get('admin_note', '').strip() if hasattr(request, 'data') else ''
        
        with transaction.atomic():
            try:
                withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=request_id)
            except WithdrawalRequest.DoesNotExist:
                message = get_bilingual_error_message(
                    'Withdrawal request not found',
                    'طلب السحب غير موجود',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
            
            # Validate status
            if withdrawal_request.status != 'SUBMITTED':
                message = get_bilingual_error_message(
                    f'Cannot approve request with status: {withdrawal_request.status}',
                    f'لا يمكن الموافقة على طلب بحالة: {withdrawal_request.status}',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            withdrawal_request.status = 'APPROVED'
            withdrawal_request.reviewed_by = request.user
            withdrawal_request.reviewed_at = timezone.now()
            if admin_note:
                withdrawal_request.admin_note = admin_note
            withdrawal_request.save()
        
        logger.info(f"Withdrawal request {request_id} approved by admin {request.user.id}")
        
        message = get_bilingual_error_message(
            'Withdrawal request approved successfully',
            'تمت الموافقة على طلب السحب بنجاح',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": {
                "request_id": str(withdrawal_request.id),
                "status": withdrawal_request.status,
                "reviewed_at": withdrawal_request.reviewed_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)


class RejectWithdrawalRequestView(EMADBaseView):
    """
    Reject a withdrawal request
    POST /api/admin-panel/withdrawal-requests/<request_id>/reject/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['post']
    
    def handle_post(self, request, request_id):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get admin note (required for rejection)
        admin_note = request.data.get('admin_note', '').strip() if hasattr(request, 'data') else ''
        
        if not admin_note:
            message = get_bilingual_error_message(
                'Admin note is required when rejecting a request',
                'ملاحظة الإدارة مطلوبة عند رفض الطلب',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            try:
                withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=request_id)
            except WithdrawalRequest.DoesNotExist:
                message = get_bilingual_error_message(
                    'Withdrawal request not found',
                    'طلب السحب غير موجود',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
            
            # Validate status
            if withdrawal_request.status not in ['SUBMITTED', 'APPROVED']:
                message = get_bilingual_error_message(
                    f'Cannot reject request with status: {withdrawal_request.status}',
                    f'لا يمكن رفض طلب بحالة: {withdrawal_request.status}',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            withdrawal_request.status = 'REJECTED'
            withdrawal_request.reviewed_by = request.user
            withdrawal_request.reviewed_at = timezone.now()
            withdrawal_request.admin_note = admin_note
            withdrawal_request.save()
        
        logger.info(f"Withdrawal request {request_id} rejected by admin {request.user.id}: {admin_note}")
        
        message = get_bilingual_error_message(
            'Withdrawal request rejected',
            'تم رفض طلب السحب',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": {
                "request_id": str(withdrawal_request.id),
                "status": withdrawal_request.status,
                "reviewed_at": withdrawal_request.reviewed_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)


class CancelWithdrawalRequestView(EMADBaseView):
    """
    Cancel a withdrawal request
    POST /api/admin-panel/withdrawal-requests/<request_id>/cancel/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['post']
    
    def handle_post(self, request, request_id):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get admin note (optional)
        admin_note = request.data.get('admin_note', '').strip() if hasattr(request, 'data') else ''
        
        with transaction.atomic():
            try:
                withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=request_id)
            except WithdrawalRequest.DoesNotExist:
                message = get_bilingual_error_message(
                    'Withdrawal request not found',
                    'طلب السحب غير موجود',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
            
            # Validate status
            if withdrawal_request.status in ['PAID', 'CANCELED']:
                message = get_bilingual_error_message(
                    f'Cannot cancel request with status: {withdrawal_request.status}',
                    f'لا يمكن إلغاء طلب بحالة: {withdrawal_request.status}',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            withdrawal_request.status = 'CANCELED'
            withdrawal_request.reviewed_by = request.user
            withdrawal_request.reviewed_at = timezone.now()
            if admin_note:
                withdrawal_request.admin_note = admin_note
            withdrawal_request.save()
        
        logger.info(f"Withdrawal request {request_id} canceled by admin {request.user.id}")
        
        message = get_bilingual_error_message(
            'Withdrawal request canceled',
            'تم إلغاء طلب السحب',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": {
                "request_id": str(withdrawal_request.id),
                "status": withdrawal_request.status,
                "reviewed_at": withdrawal_request.reviewed_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)

