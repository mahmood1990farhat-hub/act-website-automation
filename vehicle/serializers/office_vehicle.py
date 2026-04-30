from rest_framework import serializers 
from .vehicle import VehicleSerializer
from ..models import OfficeVehicle
from django.db import transaction

class OfficeVehicleSerializer(serializers.ModelSerializer):
    vehicle_data = serializers.DictField(write_only = True)
    vehicle = VehicleSerializer(read_only = True)
    class Meta:
        model = OfficeVehicle
        fields = ['id', 'vehicle_data', 'vehicle'] 
    
    def create(self, validated_data):
        office = self.context.get('office' , None)
        if office is None:
            raise serializers.ValidationError({"details": "The office associated with the user cannot be determined. Please ensure that your account is linked to an office."})
        vehicle_data = validated_data.pop('vehicle_data')
        vehicle_serializer = VehicleSerializer(data =vehicle_data)
        vehicle_serializer.is_valid(raise_exception= True )
        with transaction.atomic():
            vehicle = vehicle_serializer.save()
            office_vehicle = OfficeVehicle.objects.create(vehicle = vehicle , office = office)
        return office_vehicle

