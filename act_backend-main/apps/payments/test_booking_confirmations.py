from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.payments.tasks import deliver_paid_booking_confirmations
from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


class PaidBookingConfirmationTaskTests(TestCase):
    def _trip(self):
        trip = MagicMock()
        trip.id = 42
        trip.is_paid = True
        trip.booking_confirmation_pdf = None
        trip.passenger = None
        trip.passenger_confirmation_sent_at = None
        trip.internal_booking_notification_sent_at = None

        def refresh_from_db(fields=None):
            trip.booking_confirmation_pdf = SimpleNamespace(name="booking.pdf")

        trip.refresh_from_db.side_effect = refresh_from_db
        return trip

    @patch("apps.payments.tasks.send_internal_notification", return_value=True)
    @patch("apps.payments.tasks.send_passenger_confirmation", return_value=True)
    @patch("apps.payments.tasks.ensure_booking_confirmation_pdf")
    @patch("apps.payments.tasks.Trip.objects")
    def test_pdf_and_both_emails_are_recorded_after_synchronous_acceptance(
        self, objects, ensure_pdf, passenger_send, internal_send
    ):
        trip = self._trip()
        objects.select_for_update.return_value.select_related.return_value.get.return_value = trip

        result = deliver_paid_booking_confirmations.run(42)

        ensure_pdf.assert_called_once_with(trip)
        passenger_send.assert_called_once_with(None, trip, send_now=True)
        internal_send.assert_called_once_with(trip, send_now=True)
        self.assertIsNotNone(trip.passenger_confirmation_sent_at)
        self.assertIsNotNone(trip.internal_booking_notification_sent_at)
        self.assertTrue(result["pdf_ready"])

    @patch("apps.payments.tasks.send_internal_notification")
    @patch("apps.payments.tasks.send_passenger_confirmation")
    @patch("apps.payments.tasks.ensure_booking_confirmation_pdf")
    @patch("apps.payments.tasks.Trip.objects")
    def test_existing_delivery_markers_prevent_resend(
        self, objects, ensure_pdf, passenger_send, internal_send
    ):
        trip = self._trip()
        trip.booking_confirmation_pdf = SimpleNamespace(name="booking.pdf")
        trip.passenger_confirmation_sent_at = timezone.now()
        trip.internal_booking_notification_sent_at = timezone.now()
        objects.select_for_update.return_value.select_related.return_value.get.return_value = trip

        deliver_paid_booking_confirmations.run(42)

        ensure_pdf.assert_not_called()
        passenger_send.assert_not_called()
        internal_send.assert_not_called()


class PaidBookingConfirmationDatabaseTests(TestCase):
    """Exercise real PostgreSQL row locking, not just a mocked query chain."""

    @patch("apps.payments.tasks.send_internal_notification", return_value=True)
    @patch("apps.payments.tasks.send_passenger_confirmation", return_value=True)
    def test_guest_trip_nullable_passenger_can_record_both_confirmations(
        self, passenger_send, internal_send
    ):
        vehicle = VehicleType.objects.create(
            code="guest-confirmation-test",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/test.png",
            max_passengers_count=4,
        )
        trip = Trip.objects.create(
            pickup_lat=51.4700,
            pickup_lng=-0.4543,
            dropoff_lat=51.5074,
            dropoff_lng=-0.1278,
            trip_date=timezone.localdate() + timedelta(days=2),
            trip_time=time(10, 0),
            car_type=vehicle,
            cost="112.06",
            passengers_count=1,
            passenger=None,
            passenger_name="ACT Test Guest",
            passenger_email="guest@example.invalid",
            is_guest_checkout=True,
            is_paid=True,
            booking_confirmation_pdf="trips/booking_confirmations/test.pdf",
        )

        result = deliver_paid_booking_confirmations.run(trip.id)

        trip.refresh_from_db()
        self.assertTrue(result["pdf_ready"])
        self.assertIsNotNone(trip.passenger_confirmation_sent_at)
        self.assertIsNotNone(trip.internal_booking_notification_sent_at)
        passenger_send.assert_called_once_with(None, trip, send_now=True)
        internal_send.assert_called_once_with(trip, send_now=True)

        # A duplicate webhook/confirmation run does not send duplicate email.
        deliver_paid_booking_confirmations.run(trip.id)
        passenger_send.assert_called_once()
        internal_send.assert_called_once()
