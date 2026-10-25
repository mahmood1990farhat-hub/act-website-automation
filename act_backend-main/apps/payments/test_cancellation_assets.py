"""Only the new connection to preserved mail/PDF helpers; no real delivery.

Real DRF/database cancellation. Existing provider, PDF and email boundaries mocked.
Prior template, booking, payment and full cancellation test suites are not repeated.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
import socket

from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections, transaction
from django.test import TransactionTestCase, override_settings
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.passengers.models import Passenger
from apps.trips.models import Trip
from apps.payments.models import CancellationCase
from apps.payments.cancellation_views import PassengerCancelTripView, LegacyCancelView
from apps.payments.cancellation_flow import stop_passenger_journey
from apps.payments.booking_contracts import ContractConflict
from apps.payments import cancellation_assets as assets


@override_settings(ACT_CANCELLATION_FLOW_ENABLED=True)
class CancellationAssetReuseTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.at = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
        self.user = get_user_model().objects.create(
            email='passenger@example.invalid', account_type='passenger',
            is_active=True, is_admin_verified=True, is_profile_completed=True)
        passenger = Passenger.objects.create(user=self.user)
        self.trip = Trip.objects.create(
            passenger=passenger, passenger_email=self.user.email,
            pickup_lat=0, pickup_lng=0, dropoff_lat=1, dropoff_lng=1,
            trip_date=(self.at+timedelta(days=2)).date(), trip_time=self.at.time().replace(tzinfo=None),
            passengers_count=1, cost=Decimal('100.01'), status='pending', is_paid=True)
        self.enterContext(patch('apps.payments.cancellation_views.timezone.now', return_value=self.at))
        self.process = self.enterContext(patch('apps.payments.cancellation_views.process_stopped_case'))
        self.enterContext(patch('apps.trips.services.trip_tracking.stop_trip_tracking'))
        self.pdf = self.enterContext(patch.object(assets, 'ensure_cancellation_confirmation_pdf', side_effect=self.existing_pdf))
        self.customer = self.enterContext(patch.object(assets, 'send_passenger_trip_cancellation_to_passenger', side_effect=self.passenger_email))
        self.admin = self.enterContext(patch.object(assets, 'send_passenger_trip_cancellation_to_admin', side_effect=self.admin_email))
        original = socket.socket.connect
        def local_only(sock, address):
            if isinstance(address, tuple) and address[0] not in ('127.0.0.1', 'localhost', '::1'):
                raise AssertionError('No external connection allowed in asset-bridge tests')
            return original(sock, address)
        self.enterContext(patch('socket.socket.connect', local_only))

    def existing_pdf(self, trip):
        self.assertTrue(connection.in_atomic_block)
        self.assertEqual(Trip.objects.get(pk=trip.pk).status, 'cancelled')
        if trip.cancellation_confirmation_pdf:
            return False
        trip.cancellation_confirmation_pdf = 'trips/cancellation_confirmations/synthetic.pdf'
        # Mimic the preserved FileField.save(save=True), without rendering/writing.
        trip.save()
        return True

    def passenger_email(self, user, trip):
        self.assertFalse(connection.in_atomic_block)
        self.assertEqual(user.pk, self.user.pk)
        self.assertTrue(trip.cancellation_confirmation_pdf)
        self.assertEqual(Trip.objects.get(pk=trip.pk).status, 'cancelled')
        # Existing sender's None return is not a delivery acknowledgement.
        return None

    def admin_email(self, trip):
        self.assertFalse(connection.in_atomic_block)
        self.assertEqual(Trip.objects.get(pk=trip.pk).status, 'cancelled')
        return None

    def cancel(self, user=None):
        request = APIRequestFactory().post('/synthetic/cancel/', {}, format='json')
        force_authenticate(request, user=user or self.user)
        return PassengerCancelTripView.as_view()(request, trip_id=self.trip.pk)

    def case(self):
        return CancellationCase.objects.get(receipt__trip=self.trip)

    def test_new_managed_cancellation_reuses_all_three_existing_helpers(self):
        self.assertEqual(self.cancel().status_code, 200)
        self.pdf.assert_called_once(); self.customer.assert_called_once(); self.admin.assert_called_once()
        self.assertEqual(self.customer.call_args.kwargs, {})
        self.assertEqual(len(self.customer.call_args.args), 2)
        self.trip.refresh_from_db(); self.assertEqual(self.trip.refund_status, 'manual_review')

    def test_repeat_cancellation_does_not_request_emails_again(self):
        a, b = self.cancel(), self.cancel()
        self.assertEqual(a.data['data']['cancellation_id'], b.data['data']['cancellation_id'])
        self.pdf.assert_called_once(); self.customer.assert_called_once(); self.admin.assert_called_once()

    def test_concurrent_cancellations_request_existing_assets_once(self):
        barrier = Barrier(2)
        def run(_):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait(timeout=10)
                return self.cancel(user=user).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(run, range(2))), [200, 200])
        self.assertEqual(CancellationCase.objects.count(), 1)
        self.pdf.assert_called_once(); self.customer.assert_called_once(); self.admin.assert_called_once()

    def test_provider_failure_does_not_prevent_cancellation_assets(self):
        self.process.side_effect = RuntimeError('synthetic provider unavailable')
        result = self.cancel()
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.data['data']['refund_processed'])
        self.pdf.assert_called_once(); self.customer.assert_called_once(); self.admin.assert_called_once()

    def test_existing_pdf_is_not_replaced(self):
        path = 'trips/cancellation_confirmations/already-existing.pdf'
        self.trip.cancellation_confirmation_pdf = path; self.trip.save(update_fields=['cancellation_confirmation_pdf'])
        self.assertEqual(self.cancel().status_code, 200)
        self.trip.refresh_from_db(); self.assertEqual(self.trip.cancellation_confirmation_pdf.name, path)
        self.customer.assert_called_once()

    def test_pdf_failure_does_not_undo_cancellation_or_send_placeholder_link(self):
        self.pdf.side_effect = RuntimeError('synthetic PDF fault')
        self.assertEqual(self.cancel().status_code, 200)
        self.trip.refresh_from_db(); self.assertEqual(self.trip.status, 'cancelled')
        self.customer.assert_not_called(); self.admin.assert_called_once()

    def test_pdf_silent_failure_is_not_ready(self):
        self.pdf.side_effect = lambda trip: False
        self.assertEqual(self.cancel().status_code, 200)
        self.customer.assert_not_called(); self.admin.assert_called_once()

    def test_passenger_email_error_does_not_skip_admin_or_repeat(self):
        self.customer.side_effect = RuntimeError('synthetic sender failure')
        self.assertEqual(self.cancel().status_code, 200)
        self.assertEqual(self.cancel().status_code, 200)
        self.customer.assert_called_once(); self.admin.assert_called_once()

    def test_admin_email_error_does_not_undo_cancellation(self):
        self.admin.side_effect = RuntimeError('synthetic admin sender failure')
        self.assertEqual(self.cancel().status_code, 200)
        self.trip.refresh_from_db(); self.assertEqual(self.trip.status, 'cancelled')
        self.customer.assert_called_once()

    def test_started_trip_does_not_generate_or_send_cancellation_assets(self):
        self.trip.status='active'; self.trip.save(update_fields=['status'])
        self.assertEqual(self.cancel().status_code, 409)
        self.pdf.assert_not_called(); self.customer.assert_not_called(); self.admin.assert_not_called()

    def test_unauthorised_passenger_cannot_request_assets(self):
        user = get_user_model().objects.create(email='other@example.invalid', account_type='passenger',
            is_active=True, is_admin_verified=True, is_profile_completed=True)
        Passenger.objects.create(user=user)
        self.assertEqual(self.cancel(user=user).status_code, 404)
        self.pdf.assert_not_called(); self.customer.assert_not_called(); self.admin.assert_not_called()

    def test_legacy_route_is_not_given_a_second_notification_path(self):
        with override_settings(ACT_CANCELLATION_FLOW_ENABLED=False), patch.object(
                LegacyCancelView, 'handle_post', return_value=Response({'legacy': True})) as legacy:
            self.assertEqual(self.cancel().data, {'legacy': True})
        legacy.assert_called_once()
        self.pdf.assert_not_called(); self.customer.assert_not_called(); self.admin.assert_not_called()

    def test_existing_booking_confirmation_functions_are_not_called(self):
        with patch('utils.common.email.send_passenger_confirmation') as booking_mail, patch(
                'apps.trips.services.booking_confirmation.ensure_booking_confirmation_pdf') as booking_pdf:
            self.assertEqual(self.cancel().status_code, 200)
            booking_mail.assert_not_called(); booking_pdf.assert_not_called()

    def test_helper_reports_invocation_not_smtp_acceptance(self):
        case, _ = stop_passenger_journey(self.trip.pk, actor=self.user, received_at=self.at)
        result = assets.request_existing_cancellation_assets(case.pk)
        self.assertEqual(result, {'pdf':'ready', 'passenger_email':'requested', 'admin_email':'requested'})
        self.assertNotIn('sent', result); self.assertNotIn('delivered', result)

    def test_helper_rejects_uncommitted_outer_transaction(self):
        case, _ = stop_passenger_journey(self.trip.pk, actor=self.user, received_at=self.at)
        with transaction.atomic(), self.assertRaises(ContractConflict):
            assets.request_existing_cancellation_assets(case.pk)
        self.pdf.assert_not_called(); self.customer.assert_not_called(); self.admin.assert_not_called()

    def test_email_locale_remains_the_stored_booking_language(self):
        for language in ('en','ar','fr','de','es','tr','zh'):
            with self.subTest(language=language):
                # Only demonstrate that the bridge never rewrites booking details;
                # the existing localized renderer is not re-tested or replaced.
                details = {'language':language, 'synthetic':'preserve'}
                self.trip.booking_details = details; self.trip.save(update_fields=['booking_details'])
                if not CancellationCase.objects.filter(receipt__trip=self.trip).exists():
                    stop_passenger_journey(self.trip.pk, actor=self.user, received_at=self.at)
                result = assets.request_existing_cancellation_assets(self.case().pk)
                self.assertEqual(result['passenger_email'], 'requested')
                passed_trip = self.customer.call_args.args[1]
                self.assertEqual(passed_trip.booking_details, details)
