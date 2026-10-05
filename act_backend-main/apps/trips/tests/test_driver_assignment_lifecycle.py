from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.drivers.models import BaseDriver, NormalDriver
from apps.trips.models import Trip
from apps.vehicle.models import Vehicle, VehicleType


User = get_user_model()


class DriverAssignmentLifecycleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="assignment-admin@example.invalid",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            account_type="admin",
            address="Test",
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()

        self.comfort = VehicleType.objects.create(
            code="comfort",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/comfort.png",
            max_passengers_count=4,
        )
        self.executive = VehicleType.objects.create(
            code="executive",
            name_en="Executive Class",
            name_ar="Executive Class",
            icon="vehicle_types/icons/executive.png",
            max_passengers_count=4,
        )

        self.driver1 = self._driver("driver1@example.invalid", self.comfort, "ACT-1")
        self.driver2 = self._driver("driver2@example.invalid", self.comfort, "ACT-2")
        self.executive_driver = self._driver(
            "executive@example.invalid", self.executive, "ACT-3"
        )

        self.trip = Trip.objects.create(
            pickup_lat=51.47,
            pickup_lng=-0.45,
            dropoff_lat=51.50,
            dropoff_lng=-0.12,
            trip_date=date.today() + timedelta(days=2),
            trip_time=time(12, 0),
            car_type=self.comfort,
            cost="80.00",
            passengers_count=2,
            status="pending",
            is_paid=True,
            stripe_payment_intent="pi_assignment_acceptance",
        )

        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)

    def _driver(self, email, vehicle_type, number):
        user = User.objects.create_user(
            email=email,
            password="testpass123",
            first_name="Test",
            last_name="Driver",
            account_type="normal_driver",
            address="Test",
        )
        user.is_profile_completed = True
        user.is_admin_verified = True
        user.is_active = True
        user.save()
        base = BaseDriver.objects.create(
            user=user,
            pco="driver_docs/pco/test.pdf",
            dbs="driver_docs/dbs/test.pdf",
            dvla="driver_docs/dvla/test.pdf",
        )
        vehicle = Vehicle.objects.create(
            vehicle_number=number,
            mot="vehicles/mot/test.pdf",
            year_of_manufacture=2025,
            phv="vehicles/phv/test.pdf",
            vehicle_type=vehicle_type,
        )
        NormalDriver.objects.create(driver=base, vehicle=vehicle)
        return base

    def test_admin_assignment_waits_for_selected_driver_acceptance(self):
        response = self.admin_client.post(
            f"/api/admin-panel/trips/{self.trip.id}/assign-driver/",
            {"driver_id": self.driver1.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.base_driver_id, self.driver1.id)
        self.assertEqual(self.trip.status, "pending")

        other_client = APIClient()
        other_client.force_authenticate(user=self.driver2.user)
        other_response = other_client.post(
            f"/api/trips/{self.trip.id}/accept/", {}, format="json"
        )
        self.assertEqual(other_response.status_code, 400)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "pending")
        self.assertEqual(self.trip.base_driver_id, self.driver1.id)

        assigned_client = APIClient()
        assigned_client.force_authenticate(user=self.driver1.user)
        accepted = assigned_client.post(
            f"/api/trips/{self.trip.id}/accept/", {}, format="json"
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "accepted")
        self.assertEqual(self.trip.base_driver_id, self.driver1.id)

    def test_admin_cannot_assign_wrong_vehicle_class(self):
        response = self.admin_client.post(
            f"/api/admin-panel/trips/{self.trip.id}/assign-driver/",
            {"driver_id": self.executive_driver.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.base_driver_id)
        self.assertEqual(self.trip.status, "pending")

    def test_unpaid_booking_cannot_be_assigned(self):
        self.trip.is_paid = False
        self.trip.save(update_fields=["is_paid"])
        response = self.admin_client.post(
            f"/api/admin-panel/trips/{self.trip.id}/assign-driver/",
            {"driver_id": self.driver1.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.base_driver_id)
