from rest_framework import serializers
from apps.trips.models import GuestDriverCar


class GuestDriverCarSerializer(serializers.ModelSerializer):
    """Serializer for guest driver car information"""
    
    class Meta:
        model = GuestDriverCar
        fields = [
            'id',
            'brand',
            'model',
            'color',
            'registration_number',
            'year',
            'additional_notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Validate required fields"""
        required_fields = ['brand', 'model', 'color', 'registration_number']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({
                    field: f"{field.replace('_', ' ').title()} is required"
                })
        return data
    
    def validate_year(self, value):
        """Validate year if provided"""
        if value is not None:
            from datetime import datetime
            current_year = datetime.now().year
            if value < 1900 or value > current_year + 1:  # Allow +1 for new cars
                raise serializers.ValidationError(
                    f"Year must be between 1900 and {current_year + 1}"
                )
        return value
