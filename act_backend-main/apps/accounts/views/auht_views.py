from rest_framework.permissions import AllowAny , IsAuthenticated
from utils.common import get_locale 
from django.utils.translation import gettext as _  , activate
from utils.EMDBase import EMADBaseView
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from ..models import FCMDevice
from django.contrib.auth import get_user_model
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
User = get_user_model()

def save_device_token(user , device_token):
    if device_token:

        FCMDevice.objects.update_or_create(
            device_token=device_token,
            defaults={'user': user}
        )

class LoginView(EMADBaseView):
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def handle_post(self, request):
        username = request.data.get("username")          # e-mail or phone
        password = request.data.get("password")
        account_type = request.data.get("account_type")  # "passenger" or "driver" (normal_driver, office_driver, office_owner)
        locale = get_locale(request=request)
        activate(locale)

        if not username or not password:
            message = get_bilingual_error_message(
                "Username and password are required.",
                "اسم المستخدم وكلمة المرور مطلوبان.",
                locale
            )
            return create_error_response(message, locale=locale)

        # Normalize account_type: "driver" can mean any driver type
        # Map "driver" to driver account types for validation
        driver_types = ['normal_driver', 'office_driver', 'office_owner']
        
        # Handle account_type validation
        # If account_type is not provided, we'll check the user's actual account_type after finding them
        require_account_type_validation = True
        if not account_type:
            # Account type is optional - we'll validate based on user's actual account_type
            require_account_type_validation = False
            expected_types = ['passenger', 'normal_driver', 'office_driver', 'office_owner', 'normal']
        else:
            expected_types = ['passenger'] if account_type.lower() == 'passenger' else driver_types

        # Normalize email to lowercase (emails are stored lowercase in database)
        # If username is an email, lowercase it; otherwise keep as-is (for phone numbers)
        normalized_username = username.lower() if '@' in username else username

        # 1. Does this username even exist?
        try:
            # username field is == User.USERNAME_FIELD (email, phone…)
            # Use case-insensitive lookup for email, exact match for phone
            if '@' in normalized_username:
                # Email lookup - case insensitive
                user = User.objects.get(email__iexact=normalized_username)
            else:
                # Phone number lookup - exact match
                user = User.objects.get(phone_number=normalized_username)
        except User.DoesNotExist:
            message = get_bilingual_error_message(
                "It looks like you don't have an account with us yet. Please sign up to continue.",
                "يبدو أنك لا تملك حسابًا معنا بعد. يرجى التسجيل للمتابعة.",
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)

        # 2. Check if user is active
        if not user.is_active:
            message = get_bilingual_error_message(
                "Your account has been deactivated. Please contact support for assistance.",
                "تم إلغاء تفعيل حسابك. يرجى الاتصال بالدعم للحصول على المساعدة.",
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_403_FORBIDDEN)

        # 3. Check if user is admin/staff - admins can login with any account_type or without account_type
        is_admin = user.is_staff or user.is_superuser
        is_legacy_admin = user.account_type == 'normal' or user.account_type not in ['passenger', 'normal_driver', 'office_driver', 'office_owner']
        
        # If user is admin or legacy admin, skip account_type validation
        if require_account_type_validation and not (is_admin or is_legacy_admin):
            # Check if account_type matches (only for non-admin users)
            if user.account_type not in expected_types:
                if account_type.lower() == 'passenger':
                    message = get_bilingual_error_message(
                        "This account is registered as a driver. Please use the driver login.",
                        "هذا الحساب مسجل كسائق. يرجى استخدام تسجيل الدخول للسائق.",
                        locale
                    )
                else:
                    message = get_bilingual_error_message(
                        "This account is registered as a passenger. Please use the passenger login.",
                        "هذا الحساب مسجل كراكب. يرجى استخدام تسجيل الدخول للراكب.",
                        locale
                    )
                return create_error_response(message, locale=locale, status_code=status.HTTP_403_FORBIDDEN)

        # 4. Exists → check password (use normalized username for authentication)
        authenticated_user = authenticate(request, username=normalized_username, password=password)
        if authenticated_user is None:        # password wrong
            message = get_bilingual_error_message(
                "Incorrect password. Please try again.",
                "كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى.",
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_401_UNAUTHORIZED)

        # Ensure authenticated user matches the found user
        if authenticated_user.id != user.id:
            message = get_bilingual_error_message(
                "Authentication failed. Please try again.",
                "فشل المصادقة. يرجى المحاولة مرة أخرى.",
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(authenticated_user)
        save_device_token(user=authenticated_user, device_token=request.data.get("device_token"))

        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            "first_name": authenticated_user.first_name,
            "last_name": authenticated_user.last_name,
            "email": authenticated_user.email,
            "account_type": authenticated_user.account_type,
            "user_id": authenticated_user.id,
            "is_profile_completed": authenticated_user.is_profile_completed,
            "is_admin_verified": authenticated_user.is_admin_verified,
            "is_staff": authenticated_user.is_staff,
            "is_superuser": authenticated_user.is_superuser,
            "message": _("Login successful")
        }, status=status.HTTP_200_OK)


class LogoutView(EMADBaseView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

   

    def handle_post(self, request):
        activate(get_locale(request=request))
        refresh_token = request.data.get("refresh_token")
        device_token = request.data.get('device_token')
        
        if not refresh_token:
            return Response(
                {"details": _("Refresh token is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"details": _("Invalid or expired refresh token.")},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if device_token:
            FCMDevice.objects.filter(user=request.user, device_token=device_token).delete()

        return Response(
            {"message": _("Logged out successfully.")},
            status=status.HTTP_200_OK
        )


class DeleteAccountView(EMADBaseView):
    """
    Delete account endpoint for passengers and drivers
    Users can only delete their own account
    Supports both authenticated users and inactive users (with password verification)
    """
    permission_classes = [AllowAny]  # Allow unauthenticated for inactive users
    http_method_names = ['delete', 'post']  # Support both DELETE and POST for flexibility

    def handle_delete(self, request):
        """Handle DELETE request"""
        return self._delete_account(request)
    
    def handle_post(self, request):
        """Handle POST request (for clients that don't support DELETE)"""
        # Check if this is actually a delete request
        if request.data.get('action') != 'delete':
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                "Invalid action. Use 'action': 'delete' to delete your account.",
                "إجراء غير صحيح. استخدم 'action': 'delete' لحذف حسابك.",
                locale
            )
            return create_error_response(message, locale=locale)
        return self._delete_account(request)
    
    def _delete_account(self, request):
        """Common logic for deleting account"""
        activate(get_locale(request=request))
        locale = get_locale(request=request)
        
        # Get user - either from authenticated request or from email/password
        user = None
        password_verified = False
        
        if request.user and request.user.is_authenticated:
            # User is authenticated
            user = request.user
            # If authenticated, password is optional but recommended for extra security
            password = request.data.get('password')
            if password:
                if not user.check_password(password):
                    message = get_bilingual_error_message(
                        "Incorrect password. Please provide the correct password to delete your account.",
                        "كلمة المرور غير صحيحة. يرجى تقديم كلمة المرور الصحيحة لحذف حسابك.",
                        locale
                    )
                    return create_error_response(message, locale=locale, status_code=status.HTTP_401_UNAUTHORIZED)
                password_verified = True
        else:
            # User is not authenticated (might be inactive) - require email and password
            email = request.data.get('email') or request.data.get('username')
            password = request.data.get('password')
            
            if not email or not password:
                message = get_bilingual_error_message(
                    "Email and password are required to delete your account.",
                    "البريد الإلكتروني وكلمة المرور مطلوبان لحذف حسابك.",
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Normalize email
            normalized_email = email.lower() if '@' in email else email
            
            # Find user
            try:
                if '@' in normalized_email:
                    user = User.objects.get(email__iexact=normalized_email)
                else:
                    user = User.objects.get(phone_number=normalized_email)
            except User.DoesNotExist:
                message = get_bilingual_error_message(
                    "Account not found.",
                    "الحساب غير موجود.",
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
            
            # Verify password
            if not user.check_password(password):
                message = get_bilingual_error_message(
                    "Incorrect password. Please provide the correct password to delete your account.",
                    "كلمة المرور غير صحيحة. يرجى تقديم كلمة المرور الصحيحة لحذف حسابك.",
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_401_UNAUTHORIZED)
            password_verified = True
        
        try:
            # Store user info for response
            user_email = user.email
            account_type = user.account_type
            
            # Blacklist all refresh tokens for this user
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            from rest_framework_simplejwt.tokens import RefreshToken
            
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for token in outstanding_tokens:
                try:
                    refresh = RefreshToken(token.token)
                    refresh.blacklist()
                except Exception:
                    pass  # Token might already be blacklisted or invalid
            
            # Delete FCM devices
            FCMDevice.objects.filter(user=user).delete()
            
            # Delete related notifications
            from ..models import Notification
            Notification.objects.filter(user=user).delete()
            
            # Delete the user (CASCADE will handle related models like Passenger, BaseDriver, etc.)
            user.delete()
            
            message = get_bilingual_error_message(
                "Your account has been deleted successfully.",
                "تم حذف حسابك بنجاح.",
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'account_type': account_type
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting account for user {user.id}: {str(e)}", exc_info=True)
            
            message = get_bilingual_error_message(
                "An error occurred while deleting your account. Please try again or contact support.",
                "حدث خطأ أثناء حذف حسابك. يرجى المحاولة مرة أخرى أو الاتصال بالدعم.",
                locale
            )
            from utils.common.error_handlers import create_exception_error_response
            return create_exception_error_response(e, locale, message)


class TokenRefreshView(EMADBaseView):
    """
    Refresh JWT access token using refresh token
    Works for all user types (passengers, drivers, admins)
    
    This endpoint implements token rotation for security:
    - Old refresh token is blacklisted
    - New access token and refresh token are returned
    """
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def handle_post(self, request):
        activate(get_locale(request=request))
        refresh_token = request.data.get("refresh_token")
        
        if not refresh_token:
            raise ValidationError({"error": _("Refresh token is required.")})
        
        try:
            # Validate the refresh token
            refresh = RefreshToken(refresh_token)
            
            # Get the user from the token
            user_id = refresh.get('user_id')
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValidationError({"error": _("User not found.")})
            
            # Check if user is active (unless using custom auth rule that allows inactive)
            if not user.is_active:
                raise ValidationError({"error": _("User account is inactive.")})
            
            # Blacklist the old refresh token (rotation for security)
            try:
                refresh.blacklist()
            except Exception:
                # Token might already be blacklisted or error during blacklisting
                # Continue anyway - the token is still validated above
                pass
            
            # Generate new tokens for the user
            new_refresh = RefreshToken.for_user(user)
            
            return Response({
                'access_token': str(new_refresh.access_token),
                'refresh_token': str(new_refresh),
                'message': _("Token refreshed successfully"),
                'user': {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'account_type': user.account_type,
                    'is_profile_completed': user.is_profile_completed,
                    'is_admin_verified': user.is_admin_verified,
                }
            }, status=status.HTTP_200_OK)
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Catch any other errors (invalid token, expired, etc.)
            raise ValidationError({"error": _("Invalid or expired refresh token. Please login again.")})





