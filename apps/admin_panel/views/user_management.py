"""
Admin panel views for user management (activation/deactivation)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from utils.EMDBase import EMADBaseView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, activate
from utils.common import get_locale
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    get_bilingual_error_message
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class ActivateDeactivateUserView(EMADBaseView):
    """
    Activate or deactivate a user (passenger or driver)
    POST /api/admin-panel/users/<user_id>/activate/
    POST /api/admin-panel/users/<user_id>/deactivate/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['post']
    
    def handle_post(self, request, user_id):
        # Determine action from URL path
        # Check for '/activate/' or '/deactivate/' to avoid substring matching
        if '/activate/' in request.path:
            action = 'activate'
        elif '/deactivate/' in request.path:
            action = 'deactivate'
        else:
            # Fallback: check if path ends with activate or deactivate
            if request.path.endswith('/activate/'):
                action = 'activate'
            elif request.path.endswith('/deactivate/'):
                action = 'deactivate'
            else:
                # Default to deactivate if unclear
                action = 'deactivate'
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            user = get_object_or_404(User, id=user_id)
        except Exception:
            message = get_bilingual_error_message(
                'User not found.',
                'المستخدم غير موجود.',
                locale
            )
            return create_not_found_response(message, locale)
        
        # Validate account type
        if user.account_type not in ['passenger', 'normal_driver', 'office_driver', 'office_owner']:
            message = get_bilingual_error_message(
                'Invalid account type.',
                'نوع الحساب غير صالح.',
                locale
            )
            return create_error_response(message, locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Perform action
        if action == 'activate':
            if user.is_active:
                message = get_bilingual_error_message(
                    'User is already active.',
                    'المستخدم نشط بالفعل.',
                    locale
                )
                return Response({
                    'success': False,
                    'message': message,
                    'data': {
                        'user_id': user.id,
                        'email': user.email,
                        'account_type': user.account_type,
                        'is_active': user.is_active
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.is_active = True
            user.save(update_fields=['is_active'])
            logger.info(f"Admin {request.user.id} activated user {user.id} ({user.email})")
            
            message = get_bilingual_error_message(
                'User activated successfully.',
                'تم تفعيل المستخدم بنجاح.',
                locale
            )
            
        elif action == 'deactivate':
            if not user.is_active:
                message = get_bilingual_error_message(
                    'User is already inactive.',
                    'المستخدم غير نشط بالفعل.',
                    locale
                )
                return Response({
                    'success': False,
                    'message': message,
                    'data': {
                        'user_id': user.id,
                        'email': user.email,
                        'account_type': user.account_type,
                        'is_active': user.is_active
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.is_active = False
            user.save(update_fields=['is_active'])
            logger.info(f"Admin {request.user.id} deactivated user {user.id} ({user.email})")
            
            message = get_bilingual_error_message(
                'User deactivated successfully.',
                'تم إلغاء تفعيل المستخدم بنجاح.',
                locale
            )
        else:
            message = get_bilingual_error_message(
                'Invalid action. Use "activate" or "deactivate".',
                'إجراء غير صالح. استخدم "activate" أو "deactivate".',
                locale
            )
            return create_error_response(message, locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': message,
            'data': {
                'user_id': user.id,
                'email': user.email,
                'account_type': user.account_type,
                'is_active': user.is_active,
                'full_name': user.get_full_name() or f"{user.first_name} {user.last_name}".strip()
            }
        }, status=status.HTTP_200_OK)

