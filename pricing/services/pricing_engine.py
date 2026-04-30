"""
Pricing Engine Service

Central pricing calculation engine that replaces all hardcoded logic.
Provides full pricing breakdown including base cost, VAT, airport fees, and minimum fare adjustments.
"""
from datetime import time, datetime
from decimal import Decimal
from typing import Optional, Tuple
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.pricing.models import PricingSettings, PricingTier, PeakTimeRule, AirportFee
from apps.trips.models import Airport
from apps.vehicle.models import VehicleType
from .airport_resolver import AirportResolver


@dataclass
class PricingResult:
    """
    Complete pricing breakdown for a trip.
    """
    total_cost: Decimal
    regular_vat: Decimal
    airport_vat: Decimal
    base_trip_cost: Decimal
    min_adjustment: Decimal
    peak_multiplier_applied: Decimal
    pricing_tier_used: Optional[PricingTier] = None
    airport: Optional[Airport] = None
    direction: Optional[str] = None
    
    def to_tuple(self) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        """
        Convert to tuple format compatible with existing calculate_total_cost return.
        Returns: (total_cost, regular_vat, airport_vat, base_trip_cost, min_adjustment)
        """
        return (
            self.total_cost,
            self.regular_vat,
            self.airport_vat,
            self.base_trip_cost,
            self.min_adjustment
        )


class PricingEngine:
    """
    Central pricing calculation engine.
    Replaces all hardcoded logic in utils/calculate_cost.py
    """
    
    @staticmethod
    def get_pricing_tier(vehicle_type: VehicleType, distance_miles: Decimal) -> Optional[PricingTier]:
        """
        Select the appropriate pricing tier for a given vehicle type and distance.
        
        Args:
            vehicle_type: VehicleType instance
            distance_miles: Trip distance in miles
        
        Returns:
            PricingTier instance that matches the distance, or None if no tier found
        """
        tier = PricingTier.objects.filter(
            vehicle_type=vehicle_type,
            min_distance_miles__lte=distance_miles,
            max_distance_miles__gt=distance_miles,
            is_active=True
        ).order_by('min_distance_miles').first()
        
        return tier
    
    @staticmethod
    def get_peak_multiplier(
        trip_time: time,
        trip_date: Optional[datetime] = None,
        vehicle_type: Optional[VehicleType] = None
    ) -> Decimal:
        """
        Get the peak multiplier for a given trip time.
        Checks both vehicle-specific and global peak rules.
        
        Args:
            trip_time: Time of the trip
            trip_date: Optional date of trip (for day-of-week calculation)
            vehicle_type: Optional vehicle type (for vehicle-specific rules)
        
        Returns:
            Multiplier to apply (defaults to 1.0 if no rule matches)
        """
        settings = PricingSettings.get_settings()
        
        # Get day of week (0=Monday, 6=Sunday)
        if trip_date:
            day_of_week = trip_date.weekday()
        else:
            # Use current date if not provided
            day_of_week = timezone.now().weekday()
        
        # Query active peak rules, ordered by priority (highest first)
        # Check vehicle-specific rules first, then global rules
        rules = PeakTimeRule.objects.filter(
            is_active=True
        ).order_by('-priority', 'start_time')
        
        for rule in rules:
            # Check if rule applies to this vehicle type (or is global)
            if rule.vehicle_type and rule.vehicle_type != vehicle_type:
                continue
            
            # Check if rule applies to this day of week
            if day_of_week not in rule.days_of_week:
                continue
            
            # Check if trip_time falls within rule's time range
            # Handle time ranges that span midnight
            if rule.start_time <= rule.end_time:
                # Normal case: start_time < end_time (e.g., 07:00-10:00)
                if rule.start_time <= trip_time <= rule.end_time:
                    return rule.multiplier
            else:
                # Edge case: start_time > end_time (e.g., 22:00-02:00, spans midnight)
                if trip_time >= rule.start_time or trip_time <= rule.end_time:
                    return rule.multiplier
        
        # No matching rule found, use default multiplier
        return settings.default_peak_multiplier
    
    @staticmethod
    def get_airport_fee_for_leg(
        airport: Airport,
        direction: str,
        vehicle_type: Optional[VehicleType] = None,
    ) -> Decimal:
        """
        Get airport fee for a given airport and direction.
        Checks for vehicle-specific fees first, then falls back to default airport fees.
        
        Args:
            airport: كائن المطار المستخدم لهذه النقطة (انطلاق أو وصول)
            direction: 'from' أو 'to' حسب اتجاه الرحلة بالنسبة لهذا المطار
            vehicle_type: نوع المركبة (لرسوم خاصة بالمركبة إن وُجدت)
        
        Returns:
            قيمة رسم المطار لهذه النقطة فقط
        """
        # Check for vehicle-specific fee override
        if vehicle_type:
            try:
                airport_fee = AirportFee.objects.get(
                    airport=airport,
                    vehicle_type=vehicle_type
                )
                if direction == 'from':
                    return Decimal(str(airport_fee.pickup_fee))
                else:
                    return Decimal(str(airport_fee.dropoff_fee))
            except AirportFee.DoesNotExist:
                pass
        
        # Check vehicle_specific_fees JSON field (legacy/alternative method)
        if vehicle_type and airport.vehicle_specific_fees:
            vehicle_id_str = str(vehicle_type.id)
            if vehicle_id_str in airport.vehicle_specific_fees:
                fees = airport.vehicle_specific_fees[vehicle_id_str]
                if direction == 'from':
                    return Decimal(str(fees.get('pickup_fee', 0)))
                else:
                    return Decimal(str(fees.get('dropoff_fee', 0)))
        
        # Use default airport fees
        if direction == 'from':
            return Decimal(str(airport.pickup_vat))
        else:
            return Decimal(str(airport.dropoff_vat))
    
    @staticmethod
    def calculate_trip_cost(
        trip_time: time,
        vehicle_type: VehicleType,
        distance_miles: float,
        trip_date: Optional[datetime] = None,
        pickup_lat: Optional[float] = None,
        pickup_lng: Optional[float] = None,
        dropoff_lat: Optional[float] = None,
        dropoff_lng: Optional[float] = None,
        manual_airport_id: Optional[int] = None,
    ) -> PricingResult:
        settings = PricingSettings.get_settings()
        distance_decimal = Decimal(str(distance_miles))
        
        if distance_decimal > settings.maximum_distance_miles:
            raise ValidationError({
                'distance': f"Trip distance ({distance_miles} miles) exceeds maximum supported distance ({settings.maximum_distance_miles} miles). Please contact us directly for trips over {settings.maximum_distance_miles} miles."
            })
        
        pickup_airport: Optional[Airport] = None
        dropoff_airport: Optional[Airport] = None
        if pickup_lat is not None and pickup_lng is not None and \
           dropoff_lat is not None and dropoff_lng is not None:
            airport_info = AirportResolver.detect_airport(
                pickup_lat, pickup_lng,
                dropoff_lat, dropoff_lng,
                manual_airport_id
            )
            pickup_airport = airport_info.get('pickup_airport')
            dropoff_airport = airport_info.get('dropoff_airport')
        
        
        pricing_tier = PricingEngine.get_pricing_tier(vehicle_type, distance_decimal)
        if pricing_tier is None:
            raise ValidationError({
                'pricing': f"No pricing tier found for {vehicle_type.name_en} at distance {distance_miles} miles"
            })
        
        peak_multiplier = PricingEngine.get_peak_multiplier(
            trip_time,
            trip_date,
            vehicle_type
        )
        
        rate_per_mile = Decimal(str(pricing_tier.rate_per_mile))
        base_trip_cost = rate_per_mile * distance_decimal * peak_multiplier
        base_trip_cost = round(base_trip_cost, 2)
        

        vat_rate = settings.vat_rate
        regular_vat = base_trip_cost * vat_rate
        regular_vat = round(regular_vat, 2)
        cost_with_vat = base_trip_cost + regular_vat
        

        airport_vat = Decimal('0.00')
        subtotal = cost_with_vat


        if pickup_airport:
            fee_from = PricingEngine.get_airport_fee_for_leg(
                pickup_airport, 'from', vehicle_type
            )
            airport_vat += fee_from
            subtotal += fee_from
        if dropoff_airport:
            fee_to = PricingEngine.get_airport_fee_for_leg(
                dropoff_airport, 'to', vehicle_type
            )
            airport_vat += fee_to
            subtotal += fee_to
        
        if subtotal >= settings.minimum_fare:
            total_cost = subtotal
            min_adjustment = Decimal('0.00')
        else:
            total_cost = settings.minimum_fare
            min_adjustment = settings.minimum_fare - subtotal
        
        total_cost = round(total_cost, 2)
        regular_vat = round(regular_vat, 2)
        airport_vat = round(airport_vat, 2)
        base_trip_cost = round(base_trip_cost, 2)
        min_adjustment = round(min_adjustment, 2)
        
        return PricingResult(
            total_cost=total_cost,
            regular_vat=regular_vat,
            airport_vat=airport_vat,
            base_trip_cost=base_trip_cost,
            min_adjustment=min_adjustment,
            peak_multiplier_applied=peak_multiplier,
            pricing_tier_used=pricing_tier,
            airport=pickup_airport or dropoff_airport,
            direction=(
                'both'
                if pickup_airport and dropoff_airport
                else ('from' if pickup_airport else ('to' if dropoff_airport else None))
            ),
        )

