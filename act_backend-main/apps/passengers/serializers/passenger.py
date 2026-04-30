from rest_framework import serializers
from ..models import Passenger
from django.db import transaction
from apps.accounts.serializers import CustomUserSerializer

class PassengerSerializer(serializers.ModelSerializer):
    user_data = serializers.DictField(write_only = True)
    class Meta:
        model = Passenger
        fields = ['user_data']

    def create(self, validated_data):
        user_data = validated_data.pop('user_data')
        user_data["account_type"] = 'passenger'
        user_data['is_profile_completed'] = True
        user_data['is_admin_verified'] = True
        user_data['is_active'] = True  
        with transaction.atomic():
            user_serializer = CustomUserSerializer(data = user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()
            user.is_active=True
            passenger = Passenger.objects.create(user = user)
            
            # Send registration confirmation email
            from utils.common.email import send_passenger_registration_confirmation
            send_passenger_registration_confirmation(user)
        return passenger
    

