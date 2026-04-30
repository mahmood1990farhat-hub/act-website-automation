"""
Unit tests for AirportResolver service.
"""
import json
from django.test import TestCase
from decimal import Decimal
from django.contrib.gis.geos import GEOSGeometry
from apps.pricing.services.airport_resolver import AirportResolver
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


class AirportResolverTestCase(TestCase):
    """Test cases for AirportResolver"""
    
    def setUp(self):
        """Set up test data"""
        # Create polygon for Heathrow Airport (approximately 1km square)
        heathrow_polygon = create_test_polygon(51.4700, -0.4543, 0.01)
        
        self.airport = Airport.objects.create(
            name_en="Heathrow Airport",
            name_ar="مطار هيثرو",
            pickup_vat=5.00,
            dropoff_vat=5.00,
            detection_area=heathrow_polygon,
            is_active=True
        )
    
    def test_find_airport_at_location(self):
        """Test finding airport at location using polygon containment"""
        # Point within airport polygon
        airport = AirportResolver.find_airport_at_location(
            51.4700, -0.4543  # Same as airport center
        )
        self.assertIsNotNone(airport)
        self.assertEqual(airport.id, self.airport.id)
        
        # Point far from airport (outside polygon)
        airport = AirportResolver.find_airport_at_location(
            51.5074, -0.1278  # Central London (far away)
        )
        self.assertIsNone(airport)
    
    def test_detect_airport_pickup_in_airport(self):
        """Test airport detection when pickup is in airport"""
        result = AirportResolver.detect_airport(
            pickup_lat=51.4700, pickup_lng=-0.4543,  # In airport
            dropoff_lat=51.5074, dropoff_lng=-0.1278  # Outside airport
        )
        
        self.assertIsNotNone(result['pickup_airport'])
        self.assertEqual(result['pickup_airport'].id, self.airport.id)
        self.assertTrue(result['pickup_in_airport'])
        self.assertFalse(result['dropoff_in_airport'])
        self.assertFalse(result['both_in_airports'])
        self.assertIsNone(result['dropoff_airport'])
    
    def test_detect_airport_dropoff_in_airport(self):
        """Test airport detection when dropoff is in airport"""
        result = AirportResolver.detect_airport(
            pickup_lat=51.5074, pickup_lng=-0.1278,  # Outside airport
            dropoff_lat=51.4700, dropoff_lng=-0.4543  # In airport
        )
        
        self.assertIsNotNone(result['dropoff_airport'])
        self.assertEqual(result['dropoff_airport'].id, self.airport.id)
        self.assertFalse(result['pickup_in_airport'])
        self.assertTrue(result['dropoff_in_airport'])
        self.assertFalse(result['both_in_airports'])
        self.assertIsNone(result['pickup_airport'])
    
    def test_detect_airport_both_in_airports(self):
        """Test airport detection when both pickup and dropoff are in airports"""
        # Create second airport with polygon
        gatwick_polygon = create_test_polygon(51.1537, -0.1821, 0.01)
        airport2 = Airport.objects.create(
            name_en="Gatwick Airport",
            name_ar="مطار جاتويك",
            pickup_vat=5.00,
            dropoff_vat=5.00,
            detection_area=gatwick_polygon,
            is_active=True,
        )
        
        result = AirportResolver.detect_airport(
            pickup_lat=51.4700, pickup_lng=-0.4543,  # Heathrow
            dropoff_lat=51.1537, dropoff_lng=-0.1821  # Gatwick
        )
        
        self.assertTrue(result['both_in_airports'])
        # يجب أن يتم اكتشاف مطارين مختلفين (Pickup و Dropoff)
        self.assertIsNotNone(result['pickup_airport'])
        self.assertIsNotNone(result['dropoff_airport'])
        self.assertEqual(result['pickup_airport'].id, self.airport.id)
        self.assertEqual(result['dropoff_airport'].id, airport2.id)
    
    def test_detect_airport_manual_override(self):
        """Test manual airport selection override"""
        result = AirportResolver.detect_airport(
            pickup_lat=51.5074, pickup_lng=-0.1278,  # Outside airport
            dropoff_lat=51.5074, dropoff_lng=-0.1278,  # Outside airport
            manual_airport_id=self.airport.id
        )
        
        # With manual override, it checks if points are within the airport's polygon
        # Since points are outside, both should be False
        self.assertFalse(result['pickup_in_airport'])
        self.assertFalse(result['dropoff_in_airport'])
    
    def test_detect_airport_no_airport(self):
        """Test when no airport is detected"""
        result = AirportResolver.detect_airport(
            pickup_lat=51.5074, pickup_lng=-0.1278,  # Central London
            dropoff_lat=51.5155, dropoff_lng=-0.0922  # Another London location
        )
        
        self.assertIsNone(result['pickup_airport'])
        self.assertIsNone(result['dropoff_airport'])
        self.assertFalse(result['pickup_in_airport'])
        self.assertFalse(result['dropoff_in_airport'])
        self.assertFalse(result['both_in_airports'])

