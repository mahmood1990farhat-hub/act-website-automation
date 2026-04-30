from rest_framework import serializers
from apps.drivers.models import BaseDriver
from apps.earnings.services.commission_resolver import CommissionResolver


class DriverCommissionSerializer(serializers.Serializer):
    """
    Serializer for driver commission percentage information
    """
    driver_id = serializers.IntegerField(read_only=True)
    driver_commission_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
        help_text="Custom commission percentage for this driver (0-100)"
    )
    effective_driver_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        help_text="Effective driver percentage (after fallback resolution)"
    )
    effective_company_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        help_text="Effective company percentage (after fallback resolution)"
    )
    fallback_source = serializers.ChoiceField(
        choices=['driver', 'vehicle', 'default'],
        read_only=True,
        help_text="Source of the commission percentage (driver-specific, vehicle rule, or default)"
    )
    
    def validate_driver_commission_percentage(self, value):
        """Validate that percentage is between 0-100"""
        if value is not None:
            if value < 0 or value > 100:
                raise serializers.ValidationError("Percentage must be between 0 and 100")
        return value
