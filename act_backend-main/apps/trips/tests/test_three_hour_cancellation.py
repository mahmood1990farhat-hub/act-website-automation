from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.passengers.models import Passenger
from apps.drivers.models import BaseDriver
from apps.earnings.models import DriverRefundLedger, CompanyRefundLedger
from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


User = get_user_model()


class ThreeHourCancellationPolicyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cancel-passenger",
            email="cancel-passenger@example.invalid",
            password="testpass123",
            first_name="Cancel",
            last_name="Passenger",
            account_type="passenger",
            address="Test",
        )
        self.user.is_profile_completed = True
        self.user.is_admin_verified = True
        self.user.is_active = True
        self.user.save()
        self.passenger = Passenger.objects.create(user=self.user)
        self.vehicle_type = VehicleType.objects.create(
            code="comfort-cancel",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/test.png",
            max_passengers_count=4,
        )
        self.driver_user = User.objects.create_user(
            username="cancel-driver",
            email="cancel-driver@example.invalid",
            password="testpass123",
            first_name="Driver",
            account_type="normal_driver",
            address="Test",
        )
        self.driver = BaseDriver.objects.create(
            user=self.driver_user,
            pco="driver_docs/pco/test.pdf",
            dbs="driver_docs/dbs/test.pdf",
            dvla="driver_docs/dvla/test.pdf",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.now = timezone.make_aware(datetime(2030, 1, 1, 9, 0, 0))

    def _trip(self, hours, minutes=0, status="pending"):
        journey_at = self.now + timedelta(hours=hours, minutes=minutes)
        return Trip.objects.create(
            passenger=self.passenger,
            pickup_lat=51.47,
            pickup_lng=-0.45,
            dropoff_lat=51.50,
            dropoff_lng=-0.12,
            trip_date=journey_at.date(),
            trip_time=journey_at.time().replace(tzinfo=None),
            car_type=self.vehicle_type,
            cost="80.00",
            passengers_count=2,
            status=status,
            is_paid=True,
            stripe_payment_intent=f"pi_cancel_{hours}_{minutes}_{status}",
        )

    @patch("apps.trips.views.passenger_trips.send_passenger_trip_cancellation_to_admin")
    @patch("apps.trips.views.passenger_trips.send_passenger_trip_cancellation_to_passenger")
    def test_exactly_three_hours_gets_full_automatic_refund(self, passenger_email, admin_email):
        trip = self._trip(3, status="accepted")
        trip.base_driver = self.driver
        trip.save(update_fields=["base_driver"])
        refund = SimpleNamespace(id="re_three_hour", amount=8000)
        with patch("apps.trips.views.passenger_trips.timezone.now", return_value=self.now), patch(
            "apps.trips.views.passenger_trips.stripe.Refund.create",
            return_value=refund,
        ) as create_refund:
            response = self.client.post(f"/api/passenger/trips/{trip.id}/cancel/", {}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["data"]["refund_processed"])
        self.assertEqual(response.data["data"]["refund_amount"], "80")
        create_refund.assert_called_once()
        trip.refresh_from_db()
        self.assertEqual(trip.status, "cancelled")
        self.assertEqual(trip.refund_status, "processed")
        self.assertEqual(trip.stripe_refund_id, "re_three_hour")
        self.assertEqual(DriverRefundLedger.objects.filter(trip=trip).count(), 0)
        self.assertEqual(CompanyRefundLedger.objects.filter(trip=trip).count(), 1)

    @patch("apps.trips.views.passenger_trips.send_passenger_trip_cancellation_to_admin")
    @patch("apps.trips.views.passenger_trips.send_passenger_trip_cancellation_to_passenger")
    def test_inside_three_hours_cancels_without_automatic_refund(self, passenger_email, admin_email):
        trip = self._trip(2, 59)
        with patch("apps.trips.views.passenger_trips.timezone.now", return_value=self.now), patch(
            "apps.trips.views.passenger_trips.stripe.Refund.create"
        ) as create_refund:
            response = self.client.post(f"/api/trips/{trip.id}/cancel/", {}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["data"]["refund_eligible"])
        create_refund.assert_not_called()
        trip.refresh_from_db()
        self.assertEqual(trip.status, "cancelled")
        self.assertEqual(trip.refund_status, "manual_review")

        support = self.client.post(
            "/api/complaints/passenger/complaints/submit/",
            {
                "trip": trip.id,
                "complaint_type": "payment_issue",
                "title": "Refund review",
                "description": "Please review the refund outcome for this cancelled booking.",
            },
            format="json",
        )
        self.assertEqual(support.status_code, 201, support.data)
        self.assertTrue(support.data["data"]["ticket_number"].startswith("COMP-"))

    def test_active_journey_cannot_be_cancelled_online(self):
        trip = self._trip(2, status="active")
        response = self.client.post(f"/api/passenger/trips/{trip.id}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        trip.refresh_from_db()
        self.assertEqual(trip.status, "active")
