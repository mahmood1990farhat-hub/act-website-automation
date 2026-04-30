from rest_framework import serializers
from ..models import CustomUser
from django.utils.translation import gettext as _ 
from django.contrib.auth.hashers import make_password
from utils.common import phone_number_is_valid
from django.db.models import Q 
from django.db import transaction
from utils.common import send_verification_code

class CustomUserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "account_type",
            "address",
            "is_active",
            "password" , 
            "confirm_password",
            "is_profile_completed",
            "is_admin_verified",
        ]
        read_only_fields = ["id", "is_active"]
        extra_kwargs = {
            "password": {"write_only": True},
        }



    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError({"password" : _("Passwords do not match.")})
        
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        errors = {}
        
        # Normalize email to lowercase for comparison (emails are stored lowercase)
        normalized_email = email.lower() if email else None
        
        # Use case-insensitive lookup for email, exact match for phone
        existing_user = CustomUser.objects.filter(
            Q(phone_number=phone_number) | Q(email__iexact=normalized_email)
        ).first()

        if existing_user:
            if existing_user.phone_number == phone_number:
                errors["phone_number"] = [
                    _("Phone number already exists."),
                    "رقم الهاتف موجود بالفعل."
                ]
            # Check email case-insensitively
            if existing_user.email and normalized_email and existing_user.email.lower() == normalized_email:
                errors["email"] = [
                    _("Email already exists."),
                    "البريد الإلكتروني موجود بالفعل."
                ]
        if errors:
            raise serializers.ValidationError(errors)
        
        attrs["phone_number"] = phone_number_is_valid(phone_number)
        # Ensure email is lowercase (will be saved lowercase anyway, but normalize here too)
        if email:
            attrs["email"] = normalized_email

        return attrs 

    def validate_account_type(self , value):
        allowed_types = ['passenger', 'normal_driver', 'office_driver', 'office_owner']
        if value not in allowed_types:
            raise serializers.ValidationError(
                _("account_type Incorrect")
            )
        return value

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data["password"] = make_password(validated_data["password"])
        with transaction.atomic():
            user = super().create(validated_data)
            # try:
            #     send_verification_code(user.phone_number)
            # except Exception as e:
            #     raise serializers.ValidationError({"twilio": _("Failed to send verification code. Please try again.")})
        return user


class UpdateCustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "address"]


