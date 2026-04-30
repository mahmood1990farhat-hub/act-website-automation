from rest_framework import serializers
from apps.accounts.serializers import InterviewSerializer
from apps.accounts.models import Interview
from .bank_info import BankDetailsSerializer
from ..models import BaseDriver , NormalDriver
from apps.vehicle.serializers import VehicleSerializer
from apps.vehicle.utils import get_vehicle_type_from_string
from .base_driver import BaseDriverSerializer
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class RegisterFullNormalDriverSerializer(serializers.Serializer):
    pco = serializers.FileField()
    dbs = serializers.FileField()
    dvla = serializers.FileField()
    
    bank_details_data = serializers.DictField(write_only=True)
    vehicle_data = serializers.DictField(write_only=True)
    interview_data = InterviewSerializer(write_only=True)

    def create(self, validated_data):
        vehicle_data = validated_data.pop('vehicle_data')
        bank_details_data = validated_data.pop('bank_details_data')
        interview_data = validated_data.pop('interview_data')
        user = self.context.get('user' , None)
        if not user:
            raise serializers.ValidationError({'details' : 'error'})
        
        # Map vehicle_type string to VehicleType ID if needed
        vehicle_type_string = vehicle_data.get('vehicle_type') or vehicle_data.get('vehicle_type_id')
        if vehicle_type_string:
            # Check if it's already an ID (integer)
            if isinstance(vehicle_type_string, int):
                # It's already an ID, use vehicle_type_id field
                vehicle_data['vehicle_type_id'] = vehicle_type_string
                vehicle_data.pop('vehicle_type', None)
            elif isinstance(vehicle_type_string, str):
                # Check if it's a numeric string (ID)
                try:
                    vehicle_type_id = int(vehicle_type_string)
                    vehicle_data['vehicle_type_id'] = vehicle_type_id
                    vehicle_data.pop('vehicle_type', None)
                except (ValueError, TypeError):
                    # It's a string like '5_seater_standard', map it to VehicleType
                    vehicle_type_obj = get_vehicle_type_from_string(vehicle_type_string)
                    if vehicle_type_obj:
                        vehicle_data['vehicle_type_id'] = vehicle_type_obj.id
                        logger.info(f"Mapped vehicle_type string '{vehicle_type_string}' to VehicleType ID {vehicle_type_obj.id}")
                    else:
                        logger.warning(f"Could not map vehicle_type string '{vehicle_type_string}' to VehicleType, setting to None")
                        vehicle_data['vehicle_type_id'] = None
                    vehicle_data.pop('vehicle_type', None)
        
        with transaction.atomic():
            vehicle_serializer = VehicleSerializer(data=vehicle_data)
            vehicle_serializer.is_valid(raise_exception=True)
            vehicle_obj = vehicle_serializer.save()

            bank_details_serializer = BankDetailsSerializer(data=bank_details_data)
            bank_details_serializer.is_valid(raise_exception=True)
            bank_details_obj = bank_details_serializer.save()

            base_driver_obj = BaseDriver.objects.create(
                user=user,
                pco=validated_data['pco'],
                dbs=validated_data['dbs'],
                dvla=validated_data['dvla'],
                bank_details=bank_details_obj
            )

            normal_driver_obj = NormalDriver.objects.create(
                driver=base_driver_obj,
                vehicle=vehicle_obj
            )
            
            Interview.objects.create(user=user, **interview_data)
            user.is_profile_completed = True 
            user.save(update_fields=['is_profile_completed'])

        return normal_driver_obj



class NormalDriverUpdateSerializer(serializers.ModelSerializer):
    driver_data = serializers.DictField(required=False)
    vehicle_data = serializers.DictField(required=False)
    class Meta:
        model = NormalDriver
        fields = ['driver_data' , 'vehicle_data']

    def update(self, instance, validated_data):
        driver_data = validated_data.pop('driver_data', None)
        vehicle_data = validated_data.pop('vehicle_data', None)
        with transaction.atomic():
            if driver_data:
                driver_serializer = BaseDriverSerializer(instance.driver, data=driver_data, partial=True)
                driver_serializer.is_valid(raise_exception=True)
                driver_serializer.save()

            if vehicle_data:
                vehicle_serializer = VehicleSerializer(instance.vehicle, data=vehicle_data, partial=True)
                vehicle_serializer.is_valid(raise_exception=True)
                vehicle_serializer.save()

        return instance

        




