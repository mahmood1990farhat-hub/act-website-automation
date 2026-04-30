"""
Serializers for admin user update operations
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.passengers.models import Passenger
from apps.drivers.models import NormalDriver, BaseDriver
from apps.vehicle.models import Vehicle
from apps.vehicle.serializers import VehicleSerializer
from apps.drivers.serializers.bank_info import BankDetailsSerializer

User = get_user_model()


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    """Serializer for updating user basic information"""
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'address',
        ]
        extra_kwargs = {
            'email': {'required': False},
            'phone_number': {'required': False},
        }
    
    def validate_email(self, value):
        """Ensure email is unique if provided"""
        if value:
            user_id = self.instance.id if self.instance else None
            if User.objects.filter(email__iexact=value).exclude(id=user_id).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_phone_number(self, value):
        """Ensure phone number is unique if provided"""
        if value:
            user_id = self.instance.id if self.instance else None
            if User.objects.filter(phone_number=value).exclude(id=user_id).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
        return value


class AdminUpdateDriverSerializer(serializers.Serializer):
    """Serializer for updating driver information"""
    user_data = serializers.DictField(required=False)
    vehicle_data = serializers.DictField(required=False)
    bank_details_data = serializers.DictField(required=False)
    pco = serializers.FileField(required=False, allow_null=True)
    dbs = serializers.FileField(required=False, allow_null=True)
    dvla = serializers.FileField(required=False, allow_null=True)
    
    def update(self, instance, validated_data):
        """Update driver information"""
        from apps.drivers.models import BankDetails
        
        user_data = validated_data.get('user_data', {})
        vehicle_data = validated_data.get('vehicle_data', {})
        bank_details_data = validated_data.get('bank_details_data', {})
        
        # Update user information
        if user_data:
            user_serializer = AdminUpdateUserSerializer(instance.driver.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
        
        # Update vehicle information
        if vehicle_data:
            vehicle = instance.vehicle
            vehicle_serializer = VehicleSerializer(vehicle, data=vehicle_data, partial=True)
            vehicle_serializer.is_valid(raise_exception=True)
            vehicle_serializer.save()
        
        # Update bank details
        if bank_details_data:
            bank_details = instance.driver.bank_details
            if bank_details:
                bank_serializer = BankDetailsSerializer(bank_details, data=bank_details_data, partial=True)
                bank_serializer.is_valid(raise_exception=True)
                bank_serializer.save()
            else:
                # Create bank details if they don't exist
                bank_serializer = BankDetailsSerializer(data=bank_details_data)
                bank_serializer.is_valid(raise_exception=True)
                bank_details = bank_serializer.save()
                instance.driver.bank_details = bank_details
                instance.driver.save()
        
        # Update driver documents
        if validated_data.get('pco'):
            instance.driver.pco = validated_data['pco']
        if validated_data.get('dbs'):
            instance.driver.dbs = validated_data['dbs']
        if validated_data.get('dvla'):
            instance.driver.dvla = validated_data['dvla']
        
        if any([validated_data.get('pco'), validated_data.get('dbs'), validated_data.get('dvla')]):
            instance.driver.save()
        
        return instance


class AdminUpdatePassengerSerializer(serializers.Serializer):
    """Serializer for updating passenger information"""
    user_data = serializers.DictField(required=False)
    
    def update(self, instance, validated_data):
        """Update passenger information"""
        user_data = validated_data.get('user_data', {})
        
        # Update user information
        if user_data:
            user_serializer = AdminUpdateUserSerializer(instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
        
        return instance

