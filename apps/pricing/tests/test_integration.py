"""
Integration tests for pricing system.
Tests the full flow from trip creation to cost calculation.
"""
import json
from django.test import TestCase
from decimal import Decimal
from datetime import time, datetime, date
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry

from apps.pricing.models import PricingSettings, PricingTier, PeakTimeRule
from apps.pricing.services.pricing_engine import PricingEngine
from apps.pricing.services.airport_resolver import AirportResolver
from apps.vehicle.models import VehicleType
from apps.trips.models import Airport
from utils.calculate_cost import calculate_total_cost


def create_test_polygon(center_lat, center_lng, size_degrees=0.01):
    """
    Create a square polygon around a center point for testing.
    size_degrees: approximate size in degrees (0.01 ≈ 1km)
    """
    # Create a square polygon around the center point
    half_size = size_degrees / 2
    coordinates = [[
        [center_lng - half_size, center_lat - half_size],  # Bottom-left
        [center_lng + half_size, center_lat - half_size],  # Bottom-right
        [center_lng + half_size, center_lat + half_size],  # Top-right
        [center_lng - half_size, center_lat + half_size],  # Top-left
        [center_lng - half_size, center_lat - half_size],  # Close polygon
    ]]
    
    geojson_data = {
        "type": "Polygon",
        "coordinates": coordinates
    }
    
    return GEOSGeometry(json.dumps(geojson_data), srid=4326)


class PricingIntegrationTestCase(TestCase):
    """Integration tests for pricing system"""
    
    def setUp(self):
        """Set up test data matching hardcoded PRICING dictionary"""
        # Create pricing settings
        self.settings = PricingSettings.get_settings()
        self.settings.vat_rate = Decimal('0.20')
        self.settings.minimum_fare = Decimal('40.00')
        self.settings.maximum_distance_miles = Decimal('90.00')
        self.settings.default_peak_multiplier = Decimal('1.0')
        self.settings.use_dynamic_pricing = True
        self.settings.save()
        
        # Create vehicle type matching "Standard PHV"
        self.vehicle_type = VehicleType.objects.create(
            name_en="Standard PHV",
            name_ar="سيارة خاصة قياسية",
            max_passengers_count=4,
            order=1
        )
        
        # Create pricing tiers matching hardcoded rates
        # Normal rates for Standard PHV
        tiers_normal = [
            (0, 10, 4.60),
            (10, 20, 3.68),
            (20, 30, 3.31),
            (30, 40, 2.82),
            (40, 50, 2.67),
            (50, 60, 2.41),
            (60, 70, 2.29),
            (70, 80, 2.17),
            (80, 90, 2.06),
        ]
        
        for min_dist, max_dist, rate in tiers_normal:
            PricingTier.objects.create(
                vehicle_type=self.vehicle_type,
                min_distance_miles=Decimal(str(min_dist)),
                max_distance_miles=Decimal(str(max_dist)),
                rate_per_mile=Decimal(str(rate)),
                order=min_dist,
                is_active=True
            )
        
        # Create peak rule with multiplier to match peak rates
        # Peak rates are approximately 6.5% higher on average
        PeakTimeRule.objects.create(
            name="Morning Peak",
            is_active=True,
            start_time=time(7, 0),
            end_time=time(10, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
            multiplier=Decimal('1.065'),  # ~6.5% increase
            vehicle_type=None,
            priority=10
        )
        
        PeakTimeRule.objects.create(
            name="Evening Peak",
            is_active=True,
            start_time=time(16, 0),
            end_time=time(19, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
            multiplier=Decimal('1.065'),
            vehicle_type=None,
            priority=10
        )
    
    def test_legacy_vs_dynamic_pricing_comparison(self):
        """Compare legacy and dynamic pricing for same inputs"""
        # Disable dynamic pricing to test legacy
        self.settings.use_dynamic_pricing = False
        self.settings.save()
        
        # Calculate with legacy
        legacy_result = calculate_total_cost(
            time(14, 0),  # Non-peak
            "Standard PHV",
            15.0,
            trip_date=None,
        )
        
        # Enable dynamic pricing
        self.settings.use_dynamic_pricing = True
        self.settings.save()
        
        # Calculate with dynamic
        dynamic_result_obj = PricingEngine.calculate_trip_cost(
            trip_time=time(14, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=15.0
        )
        dynamic_result = dynamic_result_obj.to_tuple()
        
        # Results should be very close (within rounding differences)
        # Legacy: 15 miles * 3.68 = 55.20, + 20% VAT = 66.24, min fare = 66.24
        # Dynamic: 15 miles * 3.68 = 55.20, + 20% VAT = 66.24, min fare = 66.24
        self.assertAlmostEqual(
            float(legacy_result[0]),  # total_cost
            float(dynamic_result[0]),
            places=1
        )
    
    def test_airport_auto_detection_integration(self):
        """Test airport auto-detection in pricing flow"""
        # Create airport with polygon
        airport_polygon = create_test_polygon(51.4700, -0.4543, 0.01)
        airport = Airport.objects.create(
            name_en="Test Airport",
            name_ar="مطار تجريبي",
            pickup_vat=Decimal('5.00'),
            dropoff_vat=Decimal('5.00'),
            detection_area=airport_polygon,
            is_active=True
        )
        
        # Detect airport
        airport_info = AirportResolver.detect_airport(
            pickup_lat=51.4700, pickup_lng=-0.4543,  # In airport
            dropoff_lat=51.5074, dropoff_lng=-0.1278  # Outside
        )
        
        self.assertIsNotNone(airport_info['pickup_airport'])
        
        # Calculate cost with detected airport
        result = PricingEngine.calculate_trip_cost(
            trip_time=time(14, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=15.0,
            pickup_lat=51.4700,
            pickup_lng=-0.4543,
            dropoff_lat=51.5074,
            dropoff_lng=-0.1278,
        )
        
        self.assertGreater(result.airport_vat, 0)
        self.assertIsNotNone(result.airport)
    
    def test_peak_hours_pricing(self):
        """Test peak hours pricing"""
        # Monday, 8 AM (peak hours)
        monday_8am = datetime(2024, 1, 1, 8, 0)  # Monday
        
        result = PricingEngine.calculate_trip_cost(
            trip_time=time(8, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=15.0,
            trip_date=monday_8am
        )
        
        # Should have peak multiplier applied
        self.assertGreater(result.peak_multiplier_applied, Decimal('1.0'))
    
    def test_minimum_fare_application(self):
        """Test minimum fare is applied correctly"""
        # Short trip that would be below minimum fare
        result = PricingEngine.calculate_trip_cost(
            trip_time=time(14, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=2.0  # Very short trip
        )
        
        # Total should be at least minimum fare
        self.assertGreaterEqual(result.total_cost, self.settings.minimum_fare)
        self.assertGreater(result.min_adjustment, 0)

