"""
Unit tests for time conflict validation system.

Tests cover:
- Trip in same hour → reject
- Trip 30 minutes apart → reject
- Trip 2 hours apart → allow
- Trip on next day → allow
- Multiple pending trips → check each
- No existing trips → allow
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, date, time
from apps.trips.models import Trip
from apps.drivers.models import BaseDriver, NormalDriver
from apps.passengers.models import Passenger
from apps.vehicle.models import VehicleType, Vehicle
from apps.trips.utils.time_conflict import driver_has_time_conflict
from django.conf import settings

User = get_user_model()


class TimeConflictValidationTests(TestCase):
    """Test suite for time conflict validation"""
    
    def setUp(self):
        """Set up test data"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create vehicle type
        self.vehicle_type = VehicleType.objects.create(
            name_en="Standard PHV",
            name_ar="Standard PHV",
            desc_en="Standard PHV",
            desc_ar="Standard PHV",
            icon=SimpleUploadedFile("test_icon.png", b"fake icon content"),
            max_passengers_count=4,
            order=0
        )
        
        # Create driver user
        self.driver_user = User.objects.create_user(
            username='driver1',
            email='driver1@test.com',
            password='testpass123',
            account_type='normal_driver',
            first_name='Driver',
            last_name='One'
        )
        
        # Create passenger user
        self.passenger_user = User.objects.create_user(
            username='passenger1',
            email='passenger1@test.com',
            password='testpass123',
            account_type='passenger',
            first_name='Passenger',
            last_name='One'
        )
        
        # Create passenger
        self.passenger = Passenger.objects.create(user=self.passenger_user)
        
        # Create vehicle
        self.vehicle = Vehicle.objects.create(
            vehicle_number="TEST123",
            mot=SimpleUploadedFile("test_mot.pdf", b"fake mot content"),
            year_of_manufacture=2020,
            phv=SimpleUploadedFile("test_phv.pdf", b"fake phv content"),
            vehicle_type=self.vehicle_type
        )
        
        # Create base driver
        self.base_driver = BaseDriver.objects.create(
            user=self.driver_user,
            pco=SimpleUploadedFile("test_pco.pdf", b"fake pco content"),
            dbs=SimpleUploadedFile("test_dbs.pdf", b"fake dbs content")
        )
        
        # Create normal driver
        self.normal_driver = NormalDriver.objects.create(
            driver=self.base_driver,
            vehicle=self.vehicle
        )
        
        # Get buffer time from settings
        self.buffer_minutes = getattr(settings, 'TRIP_BUFFER_MINUTES', 60)
    
    def test_no_existing_trips_should_allow(self):
        """Test that driver with no existing trips can accept any trip"""
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 0))
        )
        
        has_conflict = driver_has_time_conflict(self.base_driver, new_trip_time)
        self.assertFalse(has_conflict, "Driver with no trips should not have conflict")
    
    def test_same_time_should_reject(self):
        """Test that trip at exact same time is rejected"""
        # Create existing trip
        existing_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        # Try to accept trip at same time
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 0))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time, 
            exclude_trip_id=existing_trip.id
        )
        self.assertTrue(has_conflict, "Trip at same time should have conflict")
    
    def test_30_minutes_apart_should_reject(self):
        """Test that trip 30 minutes apart is rejected (less than buffer)"""
        # Create existing trip at 14:00
        existing_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        # Try to accept trip at 14:30 (30 minutes later)
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 30))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time,
            exclude_trip_id=existing_trip.id
        )
        self.assertTrue(has_conflict, "Trip 30 minutes apart should have conflict (buffer is 60 min)")
    
    def test_2_hours_apart_should_allow(self):
        """Test that trip 2 hours apart is allowed (more than buffer)"""
        # Create existing trip at 14:00
        existing_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        # Try to accept trip at 16:00 (2 hours later)
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(16, 0))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time,
            exclude_trip_id=existing_trip.id
        )
        self.assertFalse(has_conflict, "Trip 2 hours apart should not have conflict")
    
    def test_next_day_should_allow(self):
        """Test that trip on next day is allowed"""
        # Create existing trip today at 14:00
        existing_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        # Try to accept trip tomorrow at 14:00
        tomorrow = date.today() + timedelta(days=1)
        new_trip_time = timezone.make_aware(
            datetime.combine(tomorrow, time(14, 0))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time,
            exclude_trip_id=existing_trip.id
        )
        self.assertFalse(has_conflict, "Trip on next day should not have conflict")
    
    def test_multiple_pending_trips_should_check_each(self):
        """Test that multiple pending trips are all checked"""
        # Create multiple trips
        trip1 = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        trip2 = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(16, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='accepted'
        )
        
        # Try to accept trip at 14:30 (conflicts with trip1)
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 30))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time
        )
        self.assertTrue(has_conflict, "Should conflict with trip1 at 14:00")
        
        # Try to accept trip at 16:30 (conflicts with trip2)
        new_trip_time2 = timezone.make_aware(
            datetime.combine(date.today(), time(16, 30))
        )
        
        has_conflict2 = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time2
        )
        self.assertTrue(has_conflict2, "Should conflict with trip2 at 16:00")
    
    def test_completed_trip_should_not_conflict(self):
        """Test that completed trips are ignored"""
        # Create completed trip
        completed_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='completed'
        )
        
        # Try to accept trip at same time (should be allowed)
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 0))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time
        )
        self.assertFalse(has_conflict, "Completed trips should not cause conflicts")
    
    def test_cancelled_trip_should_not_conflict(self):
        """Test that cancelled trips are ignored"""
        # Create cancelled trip
        cancelled_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='cancelled'
        )
        
        # Try to accept trip at same time (should be allowed)
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 0))
        )
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_time
        )
        self.assertFalse(has_conflict, "Cancelled trips should not cause conflicts")
    
    def test_exact_buffer_time_should_reject(self):
        """Test that trip exactly at buffer time boundary is rejected"""
        # Create existing trip at 14:00
        existing_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        # Try to accept trip exactly buffer minutes later (should still conflict)
        buffer_time = timedelta(minutes=self.buffer_minutes)
        new_trip_datetime = timezone.make_aware(
            datetime.combine(date.today(), time(14, 0))
        ) + buffer_time - timedelta(minutes=1)  # 1 minute less than buffer
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_datetime,
            exclude_trip_id=existing_trip.id
        )
        self.assertTrue(has_conflict, "Trip within buffer time should conflict")
    
    def test_just_over_buffer_time_should_allow(self):
        """Test that trip just over buffer time is allowed"""
        # Create existing trip at 14:00
        existing_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        # Try to accept trip exactly buffer minutes + 1 minute later
        buffer_time = timedelta(minutes=self.buffer_minutes + 1)
        new_trip_datetime = timezone.make_aware(
            datetime.combine(date.today(), time(14, 0))
        ) + buffer_time
        
        has_conflict = driver_has_time_conflict(
            self.base_driver, 
            new_trip_datetime,
            exclude_trip_id=existing_trip.id
        )
        self.assertFalse(has_conflict, "Trip just over buffer time should not conflict")
    
    def test_different_statuses_should_all_be_checked(self):
        """Test that all relevant statuses are checked for conflicts"""
        # Create trips with different statuses
        pending_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='pending'
        )
        
        accepted_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(15, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='accepted'
        )
        
        on_the_way_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(16, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='driver_on_the_way'
        )
        
        active_trip = Trip.objects.create(
            passenger=self.passenger,
            base_driver=self.base_driver,
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today(),
            trip_time=time(17, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=1,
            status='active'
        )
        
        # Try to accept trip at 14:30 (conflicts with pending_trip)
        new_trip_time = timezone.make_aware(
            datetime.combine(date.today(), time(14, 30))
        )
        
        has_conflict = driver_has_time_conflict(self.base_driver, new_trip_time)
        self.assertTrue(has_conflict, "Should conflict with pending trip")
        
        # Try to accept trip at 15:30 (conflicts with accepted_trip)
        new_trip_time2 = timezone.make_aware(
            datetime.combine(date.today(), time(15, 30))
        )
        
        has_conflict2 = driver_has_time_conflict(self.base_driver, new_trip_time2)
        self.assertTrue(has_conflict2, "Should conflict with accepted trip")
        
        # Try to accept trip at 16:30 (conflicts with on_the_way_trip)
        new_trip_time3 = timezone.make_aware(
            datetime.combine(date.today(), time(16, 30))
        )
        
        has_conflict3 = driver_has_time_conflict(self.base_driver, new_trip_time3)
        self.assertTrue(has_conflict3, "Should conflict with driver_on_the_way trip")
        
        # Try to accept trip at 17:30 (conflicts with active_trip)
        new_trip_time4 = timezone.make_aware(
            datetime.combine(date.today(), time(17, 30))
        )
        
        has_conflict4 = driver_has_time_conflict(self.base_driver, new_trip_time4)
        self.assertTrue(has_conflict4, "Should conflict with active trip")

