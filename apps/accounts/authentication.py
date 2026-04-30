from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _

User = get_user_model()



class EmailOrPhoneAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either username or phone number.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Tries to authenticate using username first. If that fails, tries phone_number.
        Emails are case-insensitive (stored lowercase in database).
        """
        user = None
        
        # Normalize email to lowercase if it's an email address
        # Phone numbers are kept as-is
        normalized_username = username.lower() if username and '@' in username else username
        
        try:
            # First, try email (case-insensitive lookup)
            if normalized_username and '@' in normalized_username:
                user = User.objects.get(email__iexact=normalized_username)
            else:
                # Try phone number (exact match)
                user = User.objects.get(phone_number=normalized_username)
        except User.DoesNotExist:
            # If email lookup failed, try phone number as fallback
            if normalized_username and '@' in normalized_username:
                try:
                    user = User.objects.get(phone_number=normalized_username)
                except User.DoesNotExist:
                    return None  # Neither exists
            else:
                return None  # Neither exists

        # Check password if a user is found
        if user and user.check_password(password):
            return user
        return None  # Invalid password

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    def allow_inactive_user(user):
        return user is not None


