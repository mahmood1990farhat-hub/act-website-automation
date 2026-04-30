from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _, activate
from rest_framework_simplejwt.tokens import RefreshToken

from utils.EMDBase import EMADBaseView
from utils.common.locale_utils import get_locale
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from utils.common.otp_utils import create_otp_for_user, verify_otp_code, send_otp_email
from ..serializers.password_serializers import (
    ForgetPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def extract_first_error_message(serializer_errors):
    """
    Extract the first error message from serializer errors.
    Returns the first error message string or None.
    """
    if not serializer_errors:
        return None
    
    # Get first field
    first_field = list(serializer_errors.keys())[0]
    first_error_list = serializer_errors[first_field]
    
    if isinstance(first_error_list, list) and len(first_error_list) > 0:
        return str(first_error_list[0])
    elif isinstance(first_error_list, str):
        return first_error_list
    
    return None


class ForgetPasswordView(EMADBaseView):
    """
    Forget password endpoint - sends OTP code to user's email
    POST /api/auth/forget-password/
    """
    permission_classes = [AllowAny]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        serializer = ForgetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            # Extract first error message for main message
            first_error = extract_first_error_message(serializer.errors)
            
            message = get_bilingual_error_message(
                first_error or 'Invalid input. Please check your email address.',
                first_error or 'إدخال غير صحيح. يرجى التحقق من عنوان بريدك الإلكتروني.',
                locale
            )
            
            # Format all errors as detail
            from utils.common.error_handlers import format_validation_errors_as_detail
            detail = format_validation_errors_as_detail(serializer.errors, locale)
            
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        
        email = serializer.validated_data['email']
        
        try:
            # Get user by email
            user = User.objects.get(email__iexact=email)
            
            # Create OTP for user
            otp = create_otp_for_user(user, purpose='password_reset')
            
            # Send OTP via email
            email_sent = send_otp_email(user, otp.code, purpose='password_reset')
            
            if not email_sent:
                logger.warning(f"Failed to send OTP email to {user.email}, but OTP was created")
                # Continue anyway - OTP is created, email might be sent later
            
            message = get_bilingual_error_message(
                'OTP code has been sent to your email address. Please check your inbox.',
                'تم إرسال رمز OTP إلى عنوان بريدك الإلكتروني. يرجى التحقق من صندوق الوارد.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Don't reveal that email doesn't exist (security best practice)
            message = get_bilingual_error_message(
                'If an account exists with this email, an OTP code has been sent.',
                'إذا كان هناك حساب بهذا البريد الإلكتروني، فسيتم إرسال رمز OTP.',
                locale
            )
            return Response({
                'success': True,
                'message': message
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in forget password for {email}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again later.',
                'حدث خطأ. يرجى المحاولة مرة أخرى لاحقاً.',
                locale
            )
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


class ResetPasswordView(EMADBaseView):
    """
    Reset password endpoint - verifies OTP and resets password
    POST /api/auth/reset-password/
    """
    permission_classes = [AllowAny]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            # Extract first error message for main message
            first_error = extract_first_error_message(serializer.errors)
            
            message = get_bilingual_error_message(
                first_error or 'Invalid input. Please check your information.',
                first_error or 'إدخال غير صحيح. يرجى التحقق من معلوماتك.',
                locale
            )
            
            # Format all errors as detail
            from utils.common.error_handlers import format_validation_errors_as_detail
            detail = format_validation_errors_as_detail(serializer.errors, locale)
            
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        new_password = serializer.validated_data['new_password']
        
        try:
            # Verify OTP code
            is_valid, otp_instance, error_message = verify_otp_code(
                email=email,
                code=otp_code,
                purpose='password_reset'
            )
            
            if not is_valid:
                message = get_bilingual_error_message(
                    error_message or 'Invalid or expired OTP code. Please request a new one.',
                    error_message or 'رمز OTP غير صحيح أو منتهي الصلاحية. يرجى طلب رمز جديد.',
                    locale
                )
                return create_error_response(
                    message=message,
                    errors=None,
                    locale=locale,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message or 'Invalid or expired OTP code.'
                )
            
            # Get user from OTP instance
            user = otp_instance.user
            
            # Update user password
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            # Optionally blacklist all user's refresh tokens for security
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                outstanding_tokens = OutstandingToken.objects.filter(user=user)
                for token in outstanding_tokens:
                    try:
                        refresh = RefreshToken(token.token)
                        refresh.blacklist()
                    except Exception:
                        pass  # Token might already be blacklisted
                logger.info(f"Blacklisted all tokens for user {user.id} after password reset")
            except Exception as e:
                logger.warning(f"Failed to blacklist tokens for user {user.id}: {str(e)}")
                # Continue anyway - password is reset
            
            message = get_bilingual_error_message(
                'Password reset successfully. Please login with your new password.',
                'تم إعادة تعيين كلمة المرور بنجاح. يرجى تسجيل الدخول بكلمة المرور الجديدة.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in reset password for {email}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again later.',
                'حدث خطأ. يرجى المحاولة مرة أخرى لاحقاً.',
                locale
            )
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


class ChangePasswordView(EMADBaseView):
    """
    Change password endpoint - requires authentication
    POST /api/auth/change-password/
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user
        
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'user': user}
        )
        if not serializer.is_valid():
            # Extract first error message for main message
            first_error = extract_first_error_message(serializer.errors)
            
            message = get_bilingual_error_message(
                first_error or 'Invalid input. Please check your information.',
                first_error or 'إدخال غير صحيح. يرجى التحقق من معلوماتك.',
                locale
            )
            
            # Format all errors as detail
            from utils.common.error_handlers import format_validation_errors_as_detail
            detail = format_validation_errors_as_detail(serializer.errors, locale)
            
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        try:
            # Verify old password
            if not user.check_password(old_password):
                message = get_bilingual_error_message(
                    'Current password is incorrect.',
                    'كلمة المرور الحالية غير صحيحة.',
                    locale
                )
                return create_error_response(
                    message=message,
                    errors=None,
                    locale=locale,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Current password is incorrect.'
                )
            
            # Update password
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            logger.info(f"Password changed successfully for user {user.id}")
            
            message = get_bilingual_error_message(
                'Password changed successfully.',
                'تم تغيير كلمة المرور بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error changing password for user {user.id}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again later.',
                'حدث خطأ. يرجى المحاولة مرة أخرى لاحقاً.',
                locale
            )
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

