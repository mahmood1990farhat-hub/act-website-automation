from rest_framework import serializers
from ..models import OfficeDriver
from .base_driver import BaseDriverSerializer
from django.db import transaction

class OfficeDriverSerializer(serializers.ModelSerializer):
    driver_data = serializers.DictField(write_only = True)
    driver = BaseDriverSerializer(read_only = True)
    class Meta:
        model = OfficeDriver
        fields = ['driver_data' , 'driver']
    
    def create(self, validated_data):
        office = self.context.get('office' , None)
        if office is None:
            raise serializers.ValidationError({"details": "The office associated with the user cannot be determined. Please ensure that your account is linked to an office."})
        driver_data = validated_data.pop('driver_data')
        driver_serializer = BaseDriverSerializer(data = driver_data , context = {'user_type' : 'normal_driver'})
        driver_serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            driver = driver_serializer.save()
            office_driver = OfficeDriver.objects.create(driver= driver , office = office)
        return office_driver
        
