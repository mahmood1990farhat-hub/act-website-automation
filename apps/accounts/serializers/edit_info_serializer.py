from rest_framework import serializers
from utils.common import phone_number_is_valid
from ..models import CustomUser
from django.utils.translation import gettext as _ 


class RequestEmailOrPhoneChangeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=15, required=False)

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone_number')

        if not email and not phone:
            raise serializers.ValidationError(_("You must provide either email or phone number."))

        user = self.context['request'].user

        if email and email == user.email:
            raise serializers.ValidationError(_("This is already your current email."))

        if phone and phone == user.phone_number:
            raise serializers.ValidationError(_("This is already your current phone number."))

        return attrs

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(_("Phone number already exists."))
        
        phone_number_is_valid(value)

        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("Email already exists."))

        return value



class ConfirmEmailOrPhoneChangeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)
    target = serializers.ChoiceField(choices=["email", "phone"])




