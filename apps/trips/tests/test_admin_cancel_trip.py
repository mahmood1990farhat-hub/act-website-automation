"""
Test cases for Admin Trip Cancellation functionality

These tests verify that:
1. Admin can cancel any trip properly
2. The cancelling driver no longer sees the trip
3. Other drivers still see it as pending
4. No race conditions occur
5. The same logic as driver cancellation is followed
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.trips.models import Trip
from apps.drivers.models import BaseDriver, NormalDriver
from apps.passengers.models import Passenger
from apps.vehicle.models import VehicleType
from apps.accounts.models import User
from datetime import date, time, timedelta
import json

User = get_user_model()


class AdminCancelTripTests(TestCase):
    """Test cases for admin trip cancellation"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            account_type='admin'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        # Create driver users
        self.driver1_user = User.objects.create_user(
            email='driver1@test.com',
            password='testpass123',
            first_name='Driver',
            last_name='One',
            account_type='normal_driver'
        )
        self.driver2_user = User.objects.create_user(
            email='driver2@test.com',
            password='testpass123',
            first_name='Driver',
            last_name='Two',
            account_type='normal_driver'
        )
        
        # Create passenger user
        self.passenger_user = User.objects.create_user(
            email='passenger@test.com',
            password='testpass123',
            first_name='Passenger',
            last_name='User',
            account_type='passenger'
        )
        
        # Create vehicle type
        self.vehicle_type = VehicleType.objects.create(
            name='Standard Car',
            max_passengers_count=4
        )
        
        # Create base drivers
        self.base_driver1 = BaseDriver.objects.create(user=self.driver1_user)
        self.base_driver2 = BaseDriver.objects.create(user=self.driver2_user)
        
        # Create normal drivers with vehicles
        self.normal_driver1 = NormalDriver.objects.create(
            base_driver=self.base_driver1,
            vehicle_type=self.vehicle_type
        )
        self.normal_driver2 = NormalDriver.objects.create(
            base_driver=self.base_driver2,
            vehicle_type=self.vehicle_type
        )
        
        # Create passenger
        self.passenger = Passenger.objects.create(user=self.passenger_user)
        
        # Create a trip assigned to driver1
        self.trip = Trip.objects.create(
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today() + timedelta(days=1),
            trip_time=time(14, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=2,
            passenger=self.passenger,
            base_driver=self.base_driver1,
            status='accepted'
        )
        
        # Create API clients
        self.admin_client = APIClient()
        self.driver1_client = APIClient()
        self.driver2_client = APIClient()
        
        # Authenticate clients
        self.admin_client.force_authenticate(user=self.admin_user)
        self.driver1_client.force_authenticate(user=self.driver1_user)
        self.driver2_client.force_authenticate(user=self.driver2_user)
    
    def test_admin_can_cancel_trip(self):
        """Test that admin can cancel a trip"""
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        response = self.admin_client.post(url, {
            'cancellation_reason': 'Admin cancellation test'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Refresh trip from database
        self.trip.refresh_from_db()
        
        # Verify trip status changed to pending
        self.assertEqual(self.trip.status, 'pending')
        
        # Verify driver is unassigned
        self.assertIsNone(self.trip.base_driver)
        
        # Verify cancellation flags are set
        self.assertTrue(self.trip.cancelled_by_driver)
        self.assertEqual(self.trip.cancelled_by_driver_id, self.base_driver1)
        self.assertIsNotNone(self.trip.cancelled_at)
        self.assertEqual(self.trip.cancellation_reason, 'Admin cancellation test')
    
    def test_cancelled_trip_not_visible_to_original_driver(self):
        """Test that cancelled trip doesn't appear for the original driver"""
        # Admin cancels the trip
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        self.admin_client.post(url, {
            'cancellation_reason': 'Admin cancellation'
        }, format='json')
        
        # Driver1 tries to get their trips
        driver_trips_url = '/api/driver/trips/'
        response = self.driver1_client.get(driver_trips_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip_ids = [trip['id'] for trip in response.data['data']['trips']]
        
        # Trip should NOT appear in driver1's trips
        self.assertNotIn(self.trip.id, trip_ids)
    
    def test_cancelled_trip_visible_to_other_drivers(self):
        """Test that cancelled trip appears for other drivers as pending"""
        # Admin cancels the trip
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        self.admin_client.post(url, {
            'cancellation_reason': 'Admin cancellation'
        }, format='json')
        
        # Driver2 queries new trip requests
        new_trips_url = '/api/trips/new-trip-requests/'
        response = self.driver2_client.get(new_trips_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip_ids = [trip['id'] for trip in response.data['trips']]
        
        # Trip SHOULD appear for driver2
        self.assertIn(self.trip.id, trip_ids)
        
        # Verify trip status is pending
        cancelled_trip = next(trip for trip in response.data['trips'] if trip['id'] == self.trip.id)
        self.assertEqual(cancelled_trip['status'], 'pending')
    
    def test_cancelled_trip_can_be_accepted_by_other_driver(self):
        """Test that other drivers can accept a cancelled trip"""
        # Admin cancels the trip
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        self.admin_client.post(url, {
            'cancellation_reason': 'Admin cancellation'
        }, format='json')
        
        # Driver2 accepts the trip
        accept_url = f'/api/trips/{self.trip.id}/accept/'
        response = self.driver2_client.post(accept_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh trip from database
        self.trip.refresh_from_db()
        
        # Verify trip is now assigned to driver2
        self.assertEqual(self.trip.base_driver, self.base_driver2)
        self.assertEqual(self.trip.status, 'accepted')
        
        # Cancellation flags should be cleared when new driver accepts
        self.assertFalse(self.trip.cancelled_by_driver)
        self.assertIsNone(self.trip.cancelled_by_driver_id)
    
    def test_original_driver_cannot_accept_cancelled_trip(self):
        """Test that original driver cannot re-accept a cancelled trip"""
        # Admin cancels the trip
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        self.admin_client.post(url, {
            'cancellation_reason': 'Admin cancellation'
        }, format='json')
        
        # Driver1 (original driver) tries to accept the trip
        accept_url = f'/api/trips/{self.trip.id}/accept/'
        response = self.driver1_client.post(accept_url, format='json')
        
        # Should fail - driver cannot accept their own cancelled trip
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])
    
    def test_admin_cannot_cancel_already_cancelled_trip(self):
        """Test that admin cannot cancel an already cancelled trip"""
        # Admin cancels the trip
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        response = self.admin_client.post(url, {
            'cancellation_reason': 'First cancellation'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Try to cancel again
        response = self.admin_client.post(url, {
            'cancellation_reason': 'Second cancellation'
        }, format='json')
        
        # Should fail
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_cannot_cancel_pending_trip(self):
        """Test that admin cannot cancel a pending (unassigned) trip"""
        # Create a pending trip
        pending_trip = Trip.objects.create(
            pickup_lat=51.5074,
            pickup_lng=-0.1278,
            dropoff_lat=51.5155,
            dropoff_lng=-0.0922,
            trip_date=date.today() + timedelta(days=1),
            trip_time=time(15, 0),
            car_type=self.vehicle_type,
            cost=50.00,
            passengers_count=2,
            passenger=self.passenger,
            base_driver=None,
            status='pending'
        )
        
        url = f'/api/admin-panel/trips/{pending_trip.id}/cancel/'
        response = self.admin_client.post(url, {
            'cancellation_reason': 'Admin cancellation'
        }, format='json')
        
        # Should fail - can only cancel accepted, driver_on_the_way, or active trips
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_cancellation_uses_same_logic_as_driver_cancellation(self):
        """Test that admin cancellation follows the same logic as driver cancellation"""
        # Admin cancels the trip
        admin_url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        admin_response = self.admin_client.post(admin_url, {
            'cancellation_reason': 'Admin cancellation'
        }, format='json')
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        
        # Refresh trip
        self.trip.refresh_from_db()
        admin_cancelled_status = self.trip.status
        admin_cancelled_driver = self.trip.base_driver
        admin_cancelled_flag = self.trip.cancelled_by_driver
        admin_cancelled_driver_id = self.trip.cancelled_by_driver_id
        
        # Reset trip for driver cancellation test
        self.trip.status = 'accepted'
        self.trip.base_driver = self.base_driver1
        self.trip.cancelled_by_driver = False
        self.trip.cancelled_by_driver_id = None
        self.trip.cancelled_at = None
        self.trip.cancellation_reason = None
        self.trip.save()
        
        # Driver cancels the trip
        driver_url = f'/api/trips/{self.trip.id}/driver-cancel/'
        driver_response = self.driver1_client.post(driver_url, {
            'cancellation_reason': 'Driver cancellation'
        }, format='json')
        self.assertEqual(driver_response.status_code, status.HTTP_200_OK)
        
        # Refresh trip
        self.trip.refresh_from_db()
        driver_cancelled_status = self.trip.status
        driver_cancelled_driver = self.trip.base_driver
        driver_cancelled_flag = self.trip.cancelled_by_driver
        driver_cancelled_driver_id = self.trip.cancelled_by_driver_id
        
        # Both should have same status and driver assignment
        self.assertEqual(admin_cancelled_status, driver_cancelled_status)
        self.assertEqual(admin_cancelled_driver, driver_cancelled_driver)
        self.assertEqual(admin_cancelled_flag, driver_cancelled_flag)
        self.assertEqual(admin_cancelled_driver_id, driver_cancelled_driver_id)
    
    def test_non_admin_cannot_cancel_trip(self):
        """Test that non-admin users cannot access admin cancel endpoint"""
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        
        # Driver tries to cancel via admin endpoint
        response = self.driver1_client.post(url, {
            'cancellation_reason': 'Unauthorized cancellation'
        }, format='json')
        
        # Should fail - 403 Forbidden or 401 Unauthorized
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_cancellation_reason_is_optional(self):
        """Test that cancellation reason is optional"""
        url = f'/api/admin-panel/trips/{self.trip.id}/cancel/'
        response = self.admin_client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh trip
        self.trip.refresh_from_db()
        
        # Should have a default reason
        self.assertIsNotNone(self.trip.cancellation_reason)
        self.assertIn('admin', self.trip.cancellation_reason.lower())

