from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.drivers.models import BaseDriver, NormalDriver
from apps.trips.models import Trip
from apps.vehicle.models import Vehicle, VehicleType


User = get_user_model()


class DriverAssignmentLifecycleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="assignment-admin",
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
            passenger_name="Guest Passenger",
            passenger_email="guest@example.invalid",
            is_guest_checkout=True,
        )

        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)

    def _driver(self, email, vehicle_type, number):
        user = User.objects.create_user(
            username=email.split("@")[0],
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
            pco_licence_number="TPH123456",
            driver_photo="driver_docs/photos/test.jpg",
        )
        vehicle = Vehicle.objects.create(
            vehicle_number=number,
            make="Mercedes-Benz",
            model="E-Class",
            color="Black",
            mot="vehicles/mot/test.pdf",
            year_of_manufacture=2025,
            phv="vehicles/phv/test.pdf",
            vehicle_type=vehicle_type,
        )
        NormalDriver.objects.create(driver=base, vehicle=vehicle)
        return base

    def test_driver_offer_list_excludes_unpaid_and_wrong_vehicle(self):
        client = APIClient()
        client.force_authenticate(user=self.driver1.user)
        url = '/api/trips/new-trip-requests/'
        # Verify against the existing registered route, not a new endpoint.
        from django.urls import resolve
        resolve(url)
        unpaid = Trip.objects.create(
            pickup_lat=51.47, pickup_lng=-0.45, dropoff_lat=51.50,
            dropoff_lng=-0.12, trip_date=self.trip.trip_date,
            trip_time=self.trip.trip_time, car_type=self.comfort,
            cost='100.00', passengers_count=1, status='pending', is_paid=False,
        )
        wrong = Trip.objects.create(
            pickup_lat=51.47, pickup_lng=-0.45, dropoff_lat=51.50,
            dropoff_lng=-0.12, trip_date=self.trip.trip_date,
            trip_time=self.trip.trip_time, car_type=self.executive,
            cost='100.00', passengers_count=1, status='pending', is_paid=True,
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        listed = {str(row['id']) for row in response.data['trips']}
        self.assertIn(str(self.trip.id), listed)
        self.assertNotIn(str(unpaid.id), listed)
        self.assertNotIn(str(wrong.id), listed)
        for row in response.data['trips']:
            self.assertNotIn('cost', row)
            self.assertNotIn('stripe_payment_intent', row)
            self.assertIn('driver_earnings', row)

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
        with patch(
            "apps.trips.views.accept_trip.send_trip_accepted_to_passenger"
        ) as send_driver_details:
            accepted = assigned_client.post(
                f"/api/trips/{self.trip.id}/accept/", {}, format="json"
            )
            send_driver_details.assert_called_once()
            self.assertIsNone(send_driver_details.call_args.args[0])
            self.assertEqual(
                send_driver_details.call_args.args[1].passenger_email,
                "guest@example.invalid",
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


    def test_paid_assigned_journey_reaches_completed_with_financial_ledgers(self):
        assigned = self.admin_client.post(
            f"/api/admin-panel/trips/{self.trip.id}/assign-driver/",
            {"driver_id": self.driver1.id},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200, assigned.data)

        driver_client = APIClient()
        driver_client.force_authenticate(user=self.driver1.user)
        with patch("apps.trips.views.accept_trip.send_trip_accepted_to_passenger"):
            accepted = driver_client.post(
                f"/api/trips/{self.trip.id}/accept/", {}, format="json"
            )
        self.assertEqual(accepted.status_code, 200, accepted.data)

        on_way = driver_client.post(
            f"/api/trips/{self.trip.id}/driver-on-the-way/", {}, format="json"
        )
        self.assertEqual(on_way.status_code, 200, on_way.data)

        started = driver_client.post(
            f"/api/trips/{self.trip.id}/start/", {}, format="json"
        )
        self.assertEqual(started.status_code, 200, started.data)

        with patch("apps.trips.views.end_trip.stop_trip_tracking") as stop_tracking:
            completed = driver_client.post(
                f"/api/trips/{self.trip.id}/complete/", {}, format="json"
            )
        self.assertEqual(completed.status_code, 200, completed.data)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "completed")
        self.assertEqual(self.trip.driver_earning.status, "AVAILABLE")
        self.assertEqual(str(self.trip.driver_earning.gross_amount), "80.00")
        self.assertEqual(str(self.trip.company_revenue.amount), "16.00")
        stop_tracking.assert_called_once_with(self.trip.id, reason="completed")

        # Completion is idempotent and must not duplicate financial records.
        repeated = driver_client.post(
            f"/api/trips/{self.trip.id}/complete/", {}, format="json"
        )
        self.assertEqual(repeated.status_code, 200, repeated.data)
        from apps.earnings.models import DriverEarningLedger, CompanyRevenueLedger
        self.assertEqual(DriverEarningLedger.objects.filter(trip=self.trip).count(), 1)
        self.assertEqual(CompanyRevenueLedger.objects.filter(trip=self.trip).count(), 1)
