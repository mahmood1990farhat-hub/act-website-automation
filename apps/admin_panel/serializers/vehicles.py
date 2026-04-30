from apps.vehicle.models import Vehicle , VehicleType
from rest_framework import serializers


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = '__all__'

class VehicleSerializer(serializers.ModelSerializer):
    vehicle_type = VehicleTypeSerializer()
    class Meta:
        model = Vehicle
        fields = '__all__'  