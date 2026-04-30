from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.utils.translation import gettext as _
from django.utils.translation import activate
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from utils.EMDBase import EMADBaseView
from utils.common.locale_utils import get_locale
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    get_bilingual_error_message
)
from ..models import DriverOnboardingRequest
from apps.accounts.models import FCMDevice
import logging

logger = logging.getLogger(__name__)


class DriverLoginView(EMADBaseView):
    """
    Driver login endpoint for onboarding process
    """
    http_method_names = ['post']
    permission_classes = [AllowAny]
    
    def handle_post(self, request):
        activate(get_locale(request=request))
        
        email = request.data.get('email')
        password = request.data.get('password')
        
        locale = get_locale(request=request)
        
        if not email or not password:
            message = get_bilingual_error_message(
                'Email and password are required.',
                'البريد الإلكتروني وكلمة المرور مطلوبان.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if not user:
            message = get_bilingual_error_message(
                'Invalid credentials.',
                'بيانات الاعتماد غير صحيحة.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user has an onboarding request
        try:
            onboarding_request = user.driver_onboarding_request
        except DriverOnboardingRequest.DoesNotExist:
            message = get_bilingual_error_message(
                'No onboarding request found for this user.',
                'لم يتم العثور على طلب تسجيل لهذا المستخدم.',
                locale
            )
            return create_not_found_response(message, locale)
        
        # Check if user account is active
        if not user.is_active:
            message = get_bilingual_error_message(
                'Your account is not active. Please wait for admin approval.',
                'حسابك غير نشط. يرجى انتظار موافقة المسؤول.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Save device token for push notifications
        device_token = request.data.get('device_token')
        if device_token:
            try:

                FCMDevice.objects.update_or_create(
                    device_token=device_token,
                    defaults={'user': user}
                )
                logger.info(f"Device token saved for driver user {user.id}")
            except Exception as e:
                logger.warning(f"Failed to save device token for driver user {user.id}: {str(e)}")
                # Don't fail login if device token save fails
        
        return Response({
            'message': _('Login successful.'),
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_admin_verified': user.is_admin_verified,
            },
            'onboarding_status': {
                'status': onboarding_request.status,
                'next_step': self.get_next_step_message(onboarding_request.status),
                'can_upload_documents': onboarding_request.status == 'step1_approved'
            }
        })
    
    def get_next_step_message(self, status):
        """Get user-friendly message for next step"""
        messages = {
            'pending': _('Your application is being reviewed.'),
            'step1_approved': _('Step 1 approved! Please upload your documents.'),
            'step1_rejected': _('Your initial application was not approved.'),
            'documents_uploaded': _('Documents uploaded! Waiting for final review.'),
            'final_approved': _('Congratulations! You are now an approved driver.'),
            'final_rejected': _('Your application was not approved after document review.'),
            'needs_modification': _('Please modify and resubmit your documents.'),
        }
        return messages.get(status, _('Unknown status.'))


class DriverOnboardingDashboardView(EMADBaseView):
    """
    Driver dashboard to view onboarding progress
    """
    http_method_names = ['get']
    permission_classes = []  # Will be set to IsAuthenticated in the view
    
    def handle_get(self, request):
        activate(get_locale(request=request))
        user = request.user
        
        try:
            onboarding_request = user.driver_onboarding_request
        except DriverOnboardingRequest.DoesNotExist:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'No onboarding request found.',
                'لم يتم العثور على طلب التسجيل.',
                locale
            )
            return create_not_found_response(message, locale)
        
        from ..serializers import DriverOnboardingRequestSerializer
        serializer = DriverOnboardingRequestSerializer(onboarding_request)
        
        # Determine what actions the user can take
        can_upload_documents = onboarding_request.status == 'step1_approved'
        can_resubmit_documents = onboarding_request.status == 'needs_modification'
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_admin_verified': user.is_admin_verified,
            },
            'onboarding_request': serializer.data,
            'status': onboarding_request.status,
            'next_step': self.get_next_step_message(onboarding_request.status),
            'actions': {
                'can_upload_documents': can_upload_documents,
                'can_resubmit_documents': can_resubmit_documents,
                'can_view_status': True,
            },
            'progress': self.get_progress_percentage(onboarding_request.status)
        })
    
    def get_next_step_message(self, status):
        """Get user-friendly message for next step"""
        messages = {
            'pending': _('Your application is being reviewed. Please wait for admin approval.'),
            'step1_approved': _('Step 1 approved! You can now upload your documents.'),
            'step1_rejected': _('Your initial application was not approved. You may reapply in the future.'),
            'documents_uploaded': _('Documents uploaded! Waiting for final admin review.'),
            'final_approved': _('Congratulations! You are now an approved driver and can start accepting rides.'),
            'final_rejected': _('Your application was not approved after document review.'),
            'needs_modification': _('Please modify and resubmit your documents as requested by admin.'),
        }
        return messages.get(status, _('Unknown status.'))
    
    def get_progress_percentage(self, status):
        """Get progress percentage for the onboarding process"""
        progress_map = {
            'pending': 25,
            'step1_approved': 50,
            'documents_uploaded': 75,
            'final_approved': 100,
            'step1_rejected': 0,
            'final_rejected': 0,
            'needs_modification': 75,
        }
        return progress_map.get(status, 0)
