import io
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.trips.views.download_confirmation import download_booking_confirmation
from utils.common.email import _booking_confirmation_download_url


class BookingConfirmationDownloadTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(APP_BASE_URL="https://api.example.test")
    def test_email_download_url_uses_unguessable_token_not_media_filename(self):
        token = uuid.uuid4()
        trip = SimpleNamespace(id=12, booking_confirmation_token=token)

        url = _booking_confirmation_download_url(trip)

        self.assertEqual(
            url,
            f"https://api.example.test/api/trips/booking-confirmation/{token}/",
        )
        self.assertNotIn("booking_confirmation_trip_12.pdf", url)

    @patch("apps.trips.views.download_confirmation.Trip.objects")
    def test_download_serves_paid_pdf_with_private_cache_headers(self, objects):
        token = uuid.uuid4()
        file_field = MagicMock()
        file_field.__bool__.return_value = True
        file_field.open.return_value = io.BytesIO(b"%PDF-test")
        trip = SimpleNamespace(id=12, booking_confirmation_pdf=file_field)
        objects.filter.return_value.only.return_value.first.return_value = trip

        response = download_booking_confirmation(
            self.factory.get("/"),
            token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("ACT-booking-12.pdf", response["Content-Disposition"])

    @patch("apps.trips.views.download_confirmation.Trip.objects")
    def test_missing_or_unpaid_token_is_not_disclosed(self, objects):
        objects.filter.return_value.only.return_value.first.return_value = None

        with self.assertRaises(Http404):
            download_booking_confirmation(self.factory.get("/"), uuid.uuid4())
