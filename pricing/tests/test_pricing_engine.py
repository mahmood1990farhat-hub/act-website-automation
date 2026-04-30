"""
Unit tests for PricingEngine service.
"""
import json
from django.test import TestCase
from decimal import Decimal
from datetime import time, datetime
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry

from apps.pricing.models import PricingSettings, PricingTier, PeakTimeRule
from apps.pricing.services.pricing_engine import PricingEngine, PricingResult
from apps.vehicle.models import VehicleType
from apps.trips.models import Airport


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


class PricingEngineTestCase(TestCase):
    """Test cases for PricingEngine"""
    
    def setUp(self):
        """Set up test data"""
        # Create pricing settings
        self.settings = PricingSettings.get_settings()
        self.settings.vat_rate = Decimal('0.20')
        self.settings.minimum_fare = Decimal('40.00')
        self.settings.maximum_distance_miles = Decimal('90.00')
        self.settings.default_peak_multiplier = Decimal('1.0')
        self.settings.use_dynamic_pricing = True
        self.settings.save()
        
        # Create vehicle type
        self.vehicle_type = VehicleType.objects.create(
            name_en="Standard PHV",
            name_ar="سيارة خاصة قياسية",
            max_passengers_count=4,
            order=1
        )
        
        # Create pricing tiers
        self.tier1 = PricingTier.objects.create(
            vehicle_type=self.vehicle_type,
            min_distance_miles=Decimal('0.00'),
            max_distance_miles=Decimal('10.00'),
            rate_per_mile=Decimal('4.60'),
            order=0,
            is_active=True
        )
        self.tier2 = PricingTier.objects.create(
            vehicle_type=self.vehicle_type,
            min_distance_miles=Decimal('10.00'),
            max_distance_miles=Decimal('20.00'),
            rate_per_mile=Decimal('3.68'),
            order=1,
            is_active=True
        )
        
        # Create airport with polygon
        airport_polygon = create_test_polygon(51.4700, -0.4543, 0.01)
        self.airport = Airport.objects.create(
            name_en="Test Airport",
            name_ar="مطار تجريبي",
            pickup_vat=Decimal('5.00'),
            dropoff_vat=Decimal('5.00'),
            detection_area=airport_polygon,
            is_active=True
        )
    
    def test_get_pricing_tier(self):
        """Test pricing tier selection"""
        # Distance in first tier
        tier = PricingEngine.get_pricing_tier(self.vehicle_type, Decimal('5.00'))
        self.assertEqual(tier.id, self.tier1.id)
        
        # Distance in second tier
        tier = PricingEngine.get_pricing_tier(self.vehicle_type, Decimal('15.00'))
        self.assertEqual(tier.id, self.tier2.id)
        
        # Distance exactly on boundary (should use second tier)
        tier = PricingEngine.get_pricing_tier(self.vehicle_type, Decimal('10.00'))
        self.assertEqual(tier.id, self.tier2.id)
    
    def test_get_peak_multiplier_no_rule(self):
        """Test peak multiplier when no rule matches"""
        # Time outside peak hours
        multiplier = PricingEngine.get_peak_multiplier(
            time(14, 0),  # 2 PM
            datetime.now(),
            self.vehicle_type
        )
        self.assertEqual(multiplier, Decimal('1.0'))
    
    def test_get_peak_multiplier_with_rule(self):
        """Test peak multiplier with matching rule"""
        # Create peak rule
        peak_rule = PeakTimeRule.objects.create(
            name="Test Peak",
            is_active=True,
            start_time=time(7, 0),
            end_time=time(10, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
            multiplier=Decimal('1.1'),
            vehicle_type=None,  # Global rule
            priority=10
        )
        
        # Time during peak hours on Monday
        monday = datetime(2024, 1, 1, 8, 0)  # Monday, 8 AM
        multiplier = PricingEngine.get_peak_multiplier(
            time(8, 0),
            monday,
            self.vehicle_type
        )
        self.assertEqual(multiplier, Decimal('1.1'))
    
    def test_calculate_trip_cost_basic(self):
        """Test basic trip cost calculation"""
        result = PricingEngine.calculate_trip_cost(
            trip_time=time(14, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=5.0
        )
        
        self.assertIsInstance(result, PricingResult)
        self.assertGreater(result.total_cost, 0)
        self.assertEqual(result.airport, None)
        self.assertEqual(result.direction, None)
        
        # Verify calculation: 5 miles * 4.60 = 23.00, + 20% VAT = 27.60
        # But minimum fare is 40.00, so total should be 40.00
        self.assertEqual(result.total_cost, Decimal('40.00'))
        self.assertEqual(result.min_adjustment, Decimal('12.40'))
    
    def test_calculate_trip_cost_with_airport_from(self):
        """Test trip cost calculation when pickup is in airport"""
        result = PricingEngine.calculate_trip_cost(
            trip_time=time(14, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=5.0,
            pickup_lat=51.4700,
            pickup_lng=-0.4543,
            dropoff_lat=51.5074,
            dropoff_lng=-0.1278,
        )
        
        self.assertIsNotNone(result.airport)
        self.assertEqual(result.direction, 'from')
        self.assertGreater(result.airport_vat, 0)
    
    def test_calculate_trip_cost_with_airport_to(self):
        """Test trip cost calculation when dropoff is in airport"""
        result = PricingEngine.calculate_trip_cost(
            trip_time=time(14, 0),
            vehicle_type=self.vehicle_type,
            distance_miles=5.0,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.4700,
            dropoff_lng=-0.4543,
        )
        
        self.assertIsNotNone(result.airport)
        self.assertEqual(result.direction, 'to')
        self.assertGreater(result.airport_vat, 0)
    
    def test_calculate_trip_cost_exceeds_max_distance(self):
        """Test that exceeding max distance raises error"""
        with self.assertRaises(Exception):  # ValidationError
            PricingEngine.calculate_trip_cost(
                trip_time=time(14, 0),
                vehicle_type=self.vehicle_type,
                distance_miles=100.0  # Exceeds 90 miles
            )
    
    def test_calculate_trip_cost_no_tier(self):
        """Test that missing tier raises error"""
        # Create vehicle type with no tiers
        vehicle_type2 = VehicleType.objects.create(
            name_en="Test Vehicle",
            name_ar="مركبة تجريبية",
            max_passengers_count=2,
            order=2
        )
        
        with self.assertRaises(Exception):  # ValidationError
            PricingEngine.calculate_trip_cost(
                trip_time=time(14, 0),
                vehicle_type=vehicle_type2,
                distance_miles=5.0
            )
    
    def test_get_airport_fee_default(self):
        """Test getting default airport fee (per leg)"""
        fee_from = PricingEngine.get_airport_fee_for_leg(
            self.airport,
            'from',
            self.vehicle_type
        )
        self.assertEqual(fee_from, Decimal('5.00'))

        fee_to = PricingEngine.get_airport_fee_for_leg(
            self.airport,
            'to',
            self.vehicle_type
        )
        self.assertEqual(fee_to, Decimal('5.00'))
    
    def test_get_airport_fee_vehicle_specific(self):
        """Test getting vehicle-specific airport fee (per leg)"""
        from apps.pricing.models import AirportFee
        
        # Create vehicle-specific fee
        AirportFee.objects.create(
            airport=self.airport,
            vehicle_type=self.vehicle_type,
            pickup_fee=Decimal('10.00'),
            dropoff_fee=Decimal('8.00')
        )
        
        fee_from = PricingEngine.get_airport_fee_for_leg(
            self.airport,
            'from',
            self.vehicle_type
        )
        self.assertEqual(fee_from, Decimal('10.00'))
        
        fee_to = PricingEngine.get_airport_fee_for_leg(
            self.airport,
            'to',
            self.vehicle_type
        )
        self.assertEqual(fee_to, Decimal('8.00'))

