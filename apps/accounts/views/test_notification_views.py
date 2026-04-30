"""
Test notification endpoint for debugging and testing push notifications.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext as _, activate
from utils.EMDBase import EMADBaseView
from utils.common import get_locale
from utils.common import notify_user
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class TestNotificationView(EMADBaseView):
    """
    Test endpoint to send push notifications.
    
    POST /api/auth/test-notification/
    {
        "user_id": 123,  # Optional: defaults to current user
        "title_en": "Test Notification",
        "title_ar": "إشعار تجريبي",
        "desc_en": "This is a test notification",
        "desc_ar": "هذا إشعار تجريبي",
        "locale": "en"  # Optional: defaults to 'en'
    }
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get user (default to current user, or use user_id if provided)
        user_id = request.data.get('user_id')
        if user_id:
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': _('User not found.'),
                    'error': f'User with ID {user_id} does not exist.'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            target_user = request.user
        
        # Get notification content
        title_en = request.data.get('title_en', 'Test Notification')
        title_ar = request.data.get('title_ar', 'إشعار تجريبي')
        desc_en = request.data.get('desc_en', 'This is a test notification from the API.')
        desc_ar = request.data.get('desc_ar', 'هذا إشعار تجريبي من واجهة برمجة التطبيقات.')
        notification_locale = request.data.get('locale', locale)
        mobile_url = request.data.get('mobile_url', None)
        web_url = request.data.get('web_url', None)
        
        # Check if user has device token
        from apps.accounts.models import FCMDevice
        devices = FCMDevice.objects.filter(user=target_user)
        device_count = devices.count()
        
        if device_count == 0:
            return Response({
                'success': False,
                'message': _('User has no registered device tokens.'),
                'error': f'User {target_user.email} ({target_user.id}) has no device tokens. Please login with device_token first.',
                'user_info': {
                    'id': target_user.id,
                    'email': target_user.email,
                    'account_type': target_user.account_type,
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Send notification
        try:
            logger.info(f"[TEST NOTIFICATION] Sending test notification to user {target_user.id} ({target_user.email})")
            result = notify_user(
                user=target_user.id,
                title_en=title_en,
                title_ar=title_ar,
                desc_en=desc_en,
                desc_ar=desc_ar,
                locale=notification_locale,
                mobile_url=mobile_url,
                web_url=web_url,
                use_async=False  # Use sync for testing to get immediate feedback
            )
            
            if result:
                return Response({
                    'success': True,
                    'message': _('Test notification sent successfully.'),
                    'data': {
                        'user': {
                            'id': target_user.id,
                            'email': target_user.email,
                            'account_type': target_user.account_type,
                        },
                        'notification': {
                            'title_en': title_en,
                            'title_ar': title_ar,
                            'desc_en': desc_en,
                            'desc_ar': desc_ar,
                            'locale': notification_locale,
                        },
                        'device_count': device_count,
                        'devices': [
                            {
                                'id': device.id,
                                'token_preview': device.device_token[:30] + '...' if len(device.device_token) > 30 else device.device_token,
                                'created_at': device.created_at.isoformat() if device.created_at else None,
                            }
                            for device in devices
                        ]
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': _('Failed to send test notification.'),
                    'error': 'Notification function returned False.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"[TEST NOTIFICATION] Error sending test notification: {str(e)}", exc_info=True)
            import traceback
            return Response({
                'success': False,
                'message': _('Error sending test notification.'),
                'error': str(e),
                'traceback': traceback.format_exc() if request.user.is_staff else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestNotificationToSelfView(EMADBaseView):
    """
    Quick test endpoint to send notification to current logged-in user.
    
    POST /api/auth/test-notification/self/
    {
        "title_en": "Test",  # Optional
        "desc_en": "Test message"  # Optional
    }
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        title_en = request.data.get('title_en', 'Test Notification')
        title_ar = request.data.get('title_ar', 'إشعار تجريبي')
        desc_en = request.data.get('desc_en', 'This is a test notification sent to yourself.')
        desc_ar = request.data.get('desc_ar', 'هذا إشعار تجريبي تم إرساله لنفسك.')
        
        try:
            result = notify_user(
                user=request.user.id,
                title_en=title_en,
                title_ar=title_ar,
                desc_en=desc_en,
                desc_ar=desc_ar,
                locale=locale,
                use_async=False
            )
            
            if result:
                return Response({
                    'success': True,
                    'message': _('Test notification sent to yourself successfully.'),
                    'user': {
                        'id': request.user.id,
                        'email': request.user.email,
                        'account_type': request.user.account_type,
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': _('Failed to send notification.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"[TEST NOTIFICATION] Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': _('Error sending notification.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

