from rest_framework import serializers
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
import json

from .models import PricingSettings, PricingTier, PeakTimeRule, AirportFee
from apps.vehicle.models import VehicleType
from apps.trips.models import Airport


class VehicleTypeNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for vehicle type details"""
    class Meta:
        model = VehicleType
        fields = ['id', 'name_en', 'name_ar']


class AirportNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for airport details"""
    class Meta:
        model = Airport
        fields = ['id', 'name_en', 'name_ar']


class PricingSettingsSerializer(serializers.ModelSerializer):
    """Serializer for PricingSettings (singleton)"""
    
    class Meta:
        model = PricingSettings
        fields = [
            'id', 'vat_rate', 'minimum_fare', 'maximum_distance_miles',
            'currency', 'default_peak_multiplier', 'use_dynamic_pricing'
        ]
        read_only_fields = ['id']
    
    def validate_vat_rate(self, value):
        """Validate VAT rate is between 0 and 1"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("VAT rate must be between 0 and 1 (0% to 100%)")
        return value
    
    def validate_minimum_fare(self, value):
        """Validate minimum fare is positive"""
        if value <= 0:
            raise serializers.ValidationError("Minimum fare must be greater than 0")
        return value
    
    def validate_maximum_distance_miles(self, value):
        """Validate maximum distance is positive"""
        if value <= 0:
            raise serializers.ValidationError("Maximum distance must be greater than 0")
        return value
    
    def validate_default_peak_multiplier(self, value):
        """Validate peak multiplier is positive"""
        if value <= 0:
            raise serializers.ValidationError("Peak multiplier must be greater than 0")
        return value













class PricingTierSerializer(serializers.ModelSerializer):
    vehicle_type = VehicleTypeNestedSerializer(read_only=True)
    vehicle_type_ids = serializers.PrimaryKeyRelatedField(
        queryset=VehicleType.objects.all(),
        many=True,
        write_only=True
    )

    class Meta:
        model = PricingTier
        fields = [
            'id', 'vehicle_type', 'vehicle_type_ids',
            'min_distance_miles', 'max_distance_miles',
            'rate_per_mile', 'order', 'is_active'
        ]

    def validate_min_distance_miles(self, value):
        return self._validate_non_negative(value, "Minimum distance")

    def validate_rate_per_mile(self, value):
        return self._validate_non_negative(value, "Rate per mile")

    def _validate_non_negative(self, value, field_name):
        if value < 0:
            raise serializers.ValidationError(f"{field_name} cannot be negative")
        return value

    def validate(self, attrs):
        instance = self.instance

        min_distance = attrs.get(
            'min_distance_miles',
            getattr(instance, 'min_distance_miles', None)
        )
        max_distance = attrs.get(
            'max_distance_miles',
            getattr(instance, 'max_distance_miles', None)
        )
        vehicle_types = attrs.get('vehicle_type_ids', [])

        self._validate_distance_range(min_distance, max_distance)
        for vehicle_type in vehicle_types:
            self._validate_no_overlap(
                vehicle_type,
                min_distance,
                max_distance
            )

        return attrs

    def _validate_distance_range(self, min_distance, max_distance):
        """Ensure max > min"""
        if min_distance is not None and max_distance is not None:
            if max_distance <= min_distance:
                raise serializers.ValidationError({
                    'max_distance_miles': 'Maximum distance must be greater than minimum distance'
                })

    def _validate_no_overlap(self, vehicle_type, min_distance, max_distance, instance=None):
        """Ensure no overlapping tiers"""
        qs = PricingTier.objects.filter(
            vehicle_type=vehicle_type,
            min_distance_miles__lt=max_distance,
            max_distance_miles__gt=min_distance
        )

        if instance:
            qs = qs.exclude(pk=instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                'min_distance_miles': 'This range overlaps with an existing tier',
                'max_distance_miles': 'This range overlaps with an existing tier'
            })

    def create(self, validated_data):
        vehicle_types = validated_data.pop('vehicle_type_ids', [])
        instances = []
        with transaction.atomic():
            for vehicle_type in vehicle_types:
                instances.append(PricingTier.objects.create(
                    **validated_data,
                    vehicle_type=vehicle_type,
                ))
        return instances[0]

    def update(self, instance, validated_data):
        vehicle_types = validated_data.pop('vehicle_type_ids', [])
        if vehicle_types:
            instance.vehicle_type = vehicle_types[0]
            instance.save()
        return super().update(instance, validated_data)


class PeakTimeRuleSerializer(serializers.ModelSerializer):
    vehicle_type = VehicleTypeNestedSerializer(read_only=True, allow_null=True)
    vehicle_type_ids = serializers.PrimaryKeyRelatedField(
        queryset=VehicleType.objects.all(),
        many=True,
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = PeakTimeRule
        fields = [
            'id', 'name', 'is_active', 'start_time', 'end_time',
            'days_of_week', 'multiplier', 'vehicle_type', 'vehicle_type_ids', 'priority'
        ]
    
    def to_internal_value(self, data):
        """Convert string days_of_week to Python list before validation"""
        data = data.copy()
        
        days = data.get("days_of_week")
        if isinstance(days, str):
            try:
                data["days_of_week"] = json.loads(days)
            except Exception:
                pass  
        
        return super().to_internal_value(data)

    def create(self, validated_data):
        vehicle_types = validated_data.pop('vehicle_type_ids', [])
        instances = []
        with transaction.atomic():
            if not vehicle_types:
                instances.append(PeakTimeRule.objects.create(
                    **validated_data,
                    vehicle_type=None,
                ))
            else:
                for vehicle_type in vehicle_types:
                    instances.append(PeakTimeRule.objects.create(
                        **validated_data,
                        vehicle_type=vehicle_type,
                    ))
            self._created_instances = instances
        return instances[0]

    def update(self, instance, validated_data):
        vehicle_types = validated_data.pop('vehicle_type_ids', [])
        if vehicle_types:
            instance.vehicle_type = vehicle_types[0]
            instance.save()
        return super().update(instance, validated_data)

    def validate_days_of_week(self, value):
        """Validate days_of_week format"""
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "days_of_week must be a JSON array (e.g. [0, 2])"
            )
        
        if not all(isinstance(d, int) and 0 <= d <= 6 for d in value):
            raise serializers.ValidationError(
                "days_of_week values must be integers between 0 and 6"
            )
        
        return value
  
    def validate_multiplier(self, value):
        """Validate multiplier is positive"""
        if value <= 0:
            raise serializers.ValidationError("Multiplier must be greater than 0")
        return value
    
    def validate(self, attrs):
        """Validate rule data"""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and start_time == end_time:
            raise serializers.ValidationError({
                'end_time': 'Start time and end time cannot be the same'
            })
        
        return attrs
    


class AirportFeeSerializer(serializers.ModelSerializer):
    """Serializer for AirportFee"""
    airport = AirportNestedSerializer(read_only=True)
    airport_id = serializers.PrimaryKeyRelatedField(
        queryset=Airport.objects.all(),
        source='airport',
        write_only=True
    )
    vehicle_type = VehicleTypeNestedSerializer(read_only=True)
    vehicle_type_ids = serializers.PrimaryKeyRelatedField(
        queryset=VehicleType.objects.all(),
        many=True,
        write_only=True
    )

    class Meta:
        model = AirportFee
        fields = [
            'id', 'airport', 'airport_id', 'vehicle_type', 'vehicle_type_ids',
            'pickup_fee', 'dropoff_fee'
        ]
    
    def validate_pickup_fee(self, value):
        """Validate pickup fee is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Pickup fee cannot be negative")
        return value
    
    def validate_dropoff_fee(self, value):
        """Validate dropoff fee is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Dropoff fee cannot be negative")
        return value
    
    def validate(self, attrs):
        airport = attrs.get('airport')
        vehicle_types = attrs.get('vehicle_type_ids', [])
        instance = self.instance

        existing = AirportFee.objects.filter(
            airport=airport,
            vehicle_type__in=vehicle_types
        ).select_related('vehicle_type')

        if instance:
            existing = existing.exclude(pk=instance.pk)

        if existing.exists():
            errors = []

            for fee in existing:
                errors.append(
                    f"Vehicle type '{fee.vehicle_type.name_en}' already has a fee for airport '{airport.name_en}'"
                )

            raise serializers.ValidationError({
                'vehicle_type_ids': errors
            })

        return attrs

    def create(self, validated_data):
        vehicle_types = validated_data.pop('vehicle_type_ids')

        objs = []

        for vehicle_type in vehicle_types:
            obj = AirportFee(
                vehicle_type=vehicle_type,
                **validated_data
            )
            objs.append(obj)

        return AirportFee.objects.bulk_create(objs)

    def update(self, instance, validated_data):
        vehicle_types = validated_data.pop('vehicle_type_ids', [])
        if vehicle_types:
            instance.vehicle_type = vehicle_types[0]
            instance.save()
        return super().update(instance, validated_data)
