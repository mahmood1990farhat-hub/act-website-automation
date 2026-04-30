from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


class ForgetPasswordSerializer(serializers.Serializer):
    """Serializer for forget password request"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate that email exists in the system"""
        normalized_email = value.lower()
        try:
            user = User.objects.get(email__iexact=normalized_email)
            if not user.is_active:
                raise serializers.ValidationError("This account is inactive. Please contact support.")
            return normalized_email
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset with OTP verification"""
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate_email(self, value):
        """Normalize email to lowercase"""
        return value.lower() if value else value
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits.")
        if len(value) != 6:
            raise serializers.ValidationError("OTP code must be 6 digits.")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation and strength"""
        new_password = attrs.get('new_password')
        confirm_new_password = attrs.get('confirm_new_password')
        
        # Check if passwords match
        if new_password != confirm_new_password:
            raise serializers.ValidationError({
                'confirm_new_password': 'Passwords do not match.'
            })
        
        # Validate password strength using Django's password validators
        try:
            # Get user to validate password (if available)
            email = attrs.get('email')
            if email:
                try:
                    user = User.objects.get(email__iexact=email)
                    validate_password(new_password, user=user)
                except User.DoesNotExist:
                    # User doesn't exist, but we'll validate password format anyway
                    validate_password(new_password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (requires authentication)"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate(self, attrs):
        """Validate password confirmation and strength"""
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        confirm_new_password = attrs.get('confirm_new_password')
        
        # Check if passwords match
        if new_password != confirm_new_password:
            raise serializers.ValidationError({
                'confirm_new_password': 'Passwords do not match.'
            })
        
        # Check if new password is different from old password
        if old_password == new_password:
            raise serializers.ValidationError({
                'new_password': 'New password must be different from your current password.'
            })
        
        # Validate password strength using Django's password validators
        user = self.context.get('user')
        if user:
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as e:
                raise serializers.ValidationError({
                    'new_password': list(e.messages)
                })
        
        return attrs

