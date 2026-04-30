from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from decimal import Decimal


class PricingSettings(models.Model):
    """
    Global pricing configuration - singleton pattern.
    Only one instance should exist (pk=1).
    """
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.20'),
        help_text="VAT rate as decimal (e.g., 0.20 for 20%)"
    )
    minimum_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('40.00'),
        help_text="Minimum fare amount in GBP"
    )
    maximum_distance_miles = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('90.00'),
        help_text="Maximum supported trip distance in miles"
    )
    currency = models.CharField(
        max_length=3,
        default='GBP',
        help_text="Currency code (ISO 4217)"
    )
    default_peak_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('1.0'),
        help_text="Default peak multiplier when no specific rule matches"
    )
    use_dynamic_pricing = models.BooleanField(
        default=False,
        help_text="Feature flag: Enable dynamic pricing engine (disable to use legacy hardcoded pricing)"
    )
    
    class Meta:
        verbose_name = "Pricing Settings"
        verbose_name_plural = "Pricing Settings"
    
    def save(self, *args, **kwargs):
        """Enforce singleton pattern - always save as pk=1"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of singleton"""
        raise ValidationError("Cannot delete PricingSettings singleton")
    
    def __str__(self):
        return f"Pricing Settings (Dynamic: {self.use_dynamic_pricing})"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class PricingTier(models.Model):
    """
    Distance-based pricing tiers per vehicle type.
    Each tier defines a rate per mile for a specific distance range.
    """
    vehicle_type = models.ForeignKey(
        'vehicle.VehicleType',
        on_delete=models.CASCADE,
        related_name='pricing_tiers',
        help_text="Vehicle type this pricing tier applies to"
    )
    min_distance_miles = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Minimum distance (inclusive) for this tier"
    )
    max_distance_miles = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Maximum distance (exclusive) for this tier"
    )
    rate_per_mile = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Rate per mile in GBP for this distance range"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this tier is currently active"
    )
    
    class Meta:
        ordering = ['vehicle_type', 'min_distance_miles']
        unique_together = [['vehicle_type', 'min_distance_miles', 'max_distance_miles']]
        constraints = [
            models.CheckConstraint(
                check=Q(max_distance_miles__gt=F('min_distance_miles')),
                name='pricing_tier_max_gt_min_distance'
            )
        ]
        indexes = [
            models.Index(fields=['vehicle_type', 'min_distance_miles']),
        ]
    
    def clean(self):
        """Validate tier data"""
        if self.max_distance_miles <= self.min_distance_miles:
            raise ValidationError({
                'max_distance_miles': 'Maximum distance must be greater than minimum distance'
            })
        if self.rate_per_mile < 0:
            raise ValidationError({
                'rate_per_mile': 'Rate per mile cannot be negative'
            })
    
    def __str__(self):
        return f"{self.vehicle_type.name_en}: {self.min_distance_miles}-{self.max_distance_miles}mi @ £{self.rate_per_mile}/mi"


class PeakTimeRule(models.Model):
    """
    Time-based peak/surge pricing rules.
    Supports multiple rules with priority system.
    Can be global (all vehicles) or vehicle-specific.
    """
    name = models.CharField(
        max_length=100,
        help_text="Descriptive name for this peak rule (e.g., 'Morning Rush Hour')"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rule is currently active"
    )
    start_time = models.TimeField(
        help_text="Start time for peak pricing (24-hour format)"
    )
    end_time = models.TimeField(
        help_text="End time for peak pricing (24-hour format)"
    )
    days_of_week = models.JSONField(
        default=list,
        help_text="Days of week: [0-6] where 0 = Monday"
    )
    multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('1.0'),
        help_text="Multiplier to apply to base rate (e.g., 1.2 for 20% increase)"
    )
    vehicle_type = models.ForeignKey(
        'vehicle.VehicleType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='peak_rules',
        help_text="If null, applies to all vehicles (global rule). If set, only applies to this vehicle type."
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Higher priority rules are checked first. Vehicle-specific rules typically have higher priority than global rules."
    )
    
    class Meta:
        ordering = ['-priority', 'start_time']
        indexes = [
            models.Index(fields=['is_active', 'priority']),
            models.Index(fields=['vehicle_type', 'is_active']),
        ]
    
    def clean(self):
        """Validate rule data"""
        if self.multiplier <= 0:
            raise ValidationError({
                'multiplier': 'Multiplier must be greater than 0'
            })
        if not isinstance(self.days_of_week, list):
            raise ValidationError({
                'days_of_week': 'Days of week must be a list'
            })
        if not all(0 <= day <= 6 for day in self.days_of_week):
            raise ValidationError({
                'days_of_week': 'Days must be integers between 0 (Monday) and 6 (Sunday)'
            })
    
    def __str__(self):
        vehicle_str = f" ({self.vehicle_type.name_en})" if self.vehicle_type else " (All Vehicles)"
        return f"{self.name}{vehicle_str}: {self.start_time}-{self.end_time} (x{self.multiplier})"


class AirportFee(models.Model):
    """
    Optional per-vehicle airport fees.
    Allows different airport fees for different vehicle types.
    If not set, uses airport's default pickup_vat/dropoff_vat.
    """
    airport = models.ForeignKey(
        'trips.Airport',
        on_delete=models.CASCADE,
        related_name='vehicle_fees',
        help_text="Airport this fee applies to"
    )
    vehicle_type = models.ForeignKey(
        'vehicle.VehicleType',
        on_delete=models.CASCADE,
        help_text="Vehicle type this fee applies to"
    )
    pickup_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Additional fee for pickup at this airport"
    )
    dropoff_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Additional fee for dropoff at this airport"
    )
    
    class Meta:
        unique_together = [['airport', 'vehicle_type']]
        verbose_name = "Airport Fee"
        verbose_name_plural = "Airport Fees"
    
    def __str__(self):
        return f"{self.airport.name_en} - {self.vehicle_type.name_en}: Pickup £{self.pickup_fee}, Dropoff £{self.dropoff_fee}"

