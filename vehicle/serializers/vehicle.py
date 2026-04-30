from rest_framework import serializers
from ..models import Vehicle, VehicleType
from datetime import datetime
from django.utils.translation import gettext as _ 
from .vehicle_type import VehicleTypeSerializer

class VehicleSerializer(serializers.ModelSerializer):
    # For output: show full vehicle_type object
    vehicle_type = VehicleTypeSerializer(read_only=True, allow_null=True)
    # For input: accept vehicle_type_id
    vehicle_type_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleType.objects.all(),
        source='vehicle_type',
        required=False,
        allow_null=True,
        write_only=True
    )
    
    class Meta:
        model = Vehicle
        fields = ['id', 'vehicle_number', 'mot', 'year_of_manufacture', 'phv', 'vehicle_type', 'vehicle_type_id']
    
    def validate_year_of_manufacture(self, value):
        current_year = datetime.now().year
        if value < 1950 or value > current_year:
            raise serializers.ValidationError(
                _(f"Year of manufacture must be between 1950 and {current_year}.")
            )
        return value
    
