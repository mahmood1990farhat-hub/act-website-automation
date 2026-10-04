from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from apps.payments.tasks import deliver_paid_booking_confirmations


class PaidBookingConfirmationTaskTests(SimpleTestCase):
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
