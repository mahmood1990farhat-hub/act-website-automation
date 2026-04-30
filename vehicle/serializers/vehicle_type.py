from rest_framework import serializers 
from ..models import VehicleType

class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ['id', 'name_en', 'name_ar', 'desc_en', 'desc_ar', 'icon', 'max_passengers_count', 'order']

