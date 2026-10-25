"""Changed-handler tests: real PostgreSQL/DRF and signed synthetic webhooks.

Pricing/maps/provider/notifications are mocked. No real charge, email or refund.
This is not browser consent presentation or complete refund-executor acceptance.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
import json
import socket
from threading import Barrier
import time
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, connections, close_old_connections, DatabaseError
from django.test import Client, TransactionTestCase, override_settings
from django.urls import path
from rest_framework.test import APIClient

from apps.payments.models import PendingPayment, BookingTermsAcceptance
from apps.payments.booking_contracts import ContractConflict
from apps.payments.checkout_terms import TERMS_MARKER, _confirmed_pickup
from apps.payments.views.views import stripe_webhook_view
from apps.passengers.models import Passenger
from apps.trips.models import Trip
from apps.trips.services.cancellation_policy import CANDIDATE_POLICY_VERSION
from apps.trips.views.initiate_payment import InitiatePaymentView, InitiateGuestPaymentView
from apps.vehicle.models import VehicleType

urlpatterns = [
    path('registered/', InitiatePaymentView.as_view()),
    path('guest/', InitiateGuestPaymentView.as_view()),
    path('webhook/', stripe_webhook_view),
]
TEXT = 'SYNTHETIC CHECKOUT TERMS ONLY. Not published ACT wording.'
HASH = hashlib.sha256(TEXT.encode()).hexdigest()
RELEASE = {
    'published': True, 'terms_version': 'synthetic-checkout-v1',
    'policy_version': CANDIDATE_POLICY_VERSION, 'effective_at': '2026-01-01T00:00:00+00:00',
    'locales': {'en': {'text': TEXT, 'sha256': HASH, 'pdf_sha256': 'a' * 64,
                       'url': '/documents/en/synthetic-checkout-v1.pdf'}},
}
ACK = {'accepted': True, 'terms_version': 'synthetic-checkout-v1', 'terms_sha256': HASH, 'locale': 'en'}
SECRET = 'whsec_synthetic_checkout_not_a_real_secret'
INIT = 'apps.trips.views.initiate_payment.'
PAY = 'apps.payments.views.views.'


@override_settings(ROOT_URLCONF=__name__, ACT_BOOKING_TERMS_CHECKOUT_ENABLED=True,
                   ACT_BOOKING_TERMS_RELEASE=RELEASE, STRIPE_WEBHOOK_SECRET=SECRET)
class CheckoutTermsIntegrationTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor != 'postgresql':
            self.fail('These transaction/locking checks require PostgreSQL')
        original_connect = socket.socket.connect
        def local_only(sock, address):
            if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
                raise AssertionError('External network forbidden')
            return original_connect(sock, address)
        self.start_patch('socket.socket.connect', side_effect=None, new=local_only)
        self.now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        self.start_patch(INIT + 'timezone.now', return_value=self.now)
        self.user = get_user_model().objects.create(
            email='checkout@example.invalid', username='synthetic', first_name='Synthetic',
            last_name='Passenger', account_type='passenger', is_active=True,
            is_admin_verified=True, is_profile_completed=True)
        self.passenger, _ = Passenger.objects.get_or_create(user=self.user)
        self.vehicle = VehicleType.objects.create(
            code='checkout-terms-test', name_en='Test vehicle', name_ar='Test vehicle',
            max_passengers_count=4, icon='vehicle_types/icons/synthetic.png')
        self.data = {'car_type': self.vehicle.pk, 'trip_date': '2026-11-02', 'trip_time': '18:00:00',
                     'pickup_lat': 0, 'pickup_lng': 0, 'dropoff_lat': 1, 'dropoff_lng': 1,
                     'passengers_count': 1, 'large_suitcase': 0, 'small_suitcase': 0}
        self.price = {'total_cost': '100.01', 'base_trip_cost': '100.01', 'regular_vat': '0',
                      'airport_vat': '0', 'min_adjustment': '0', 'meet_and_greet_total': '0'}
        self.start_patch(INIT + 'prepare_trip_data', side_effect=lambda **kwargs: deepcopy(self.data))
        self.start_patch(INIT + 'validate_vehicle_capacity')
        self.start_patch(INIT + 'get_locale', return_value='en')
        self.start_patch(INIT + 'get_route_with_distance', return_value={'distance_miles': 5})
        from decimal import Decimal
        self.start_patch(INIT + 'calculate_authoritative_payment_price', side_effect=lambda data, car, miles, details:
                         (Decimal('100.01'), deepcopy(self.price), deepcopy(details), data['trip_time'], data['trip_date']))
        self.provider_observations = []
        def create_intent(**kwargs):
            pending_id = int(kwargs['metadata']['pending_payment_id'])
            record = BookingTermsAcceptance.objects.filter(pending_payment_id=pending_id).first()
            self.provider_observations.append({'inside_atomic': connection.in_atomic_block,
                                               'record_id': record.pk if record else None,
                                               'snapshot': deepcopy(record.snapshot) if record else None})
            return SimpleNamespace(id=f'pi_checkout_{pending_id}', client_secret='synthetic_client_secret')
        self.create_intent = self.start_patch(INIT + 'stripe.PaymentIntent.create', side_effect=create_intent)
        self.modify_intent = self.start_patch(INIT + 'stripe.PaymentIntent.modify')
        self.refund = self.start_patch(INIT + 'stripe.Refund.create', side_effect=AssertionError('No refund in checkout tests'))
        self.start_patch(PAY + 'calculate_route_safe', return_value={})
        self.queue = self.start_patch(PAY + '_queue_booking_confirmations')
        self.post_creation = self.start_patch(PAY + 'post_trip_creation')

    def start_patch(self, target, **kwargs):
        if 'new' in kwargs:
            kwargs.pop('side_effect', None)
        patcher = patch(target, **kwargs)
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked

    def checkout(self, route='guest', *, ack=ACK, details=None, anonymous=False):
        client = APIClient()
        if route == 'registered' and not anonymous:
            client.force_authenticate(self.user)
        payload = {**self.data, 'passenger_name': 'Synthetic Guest', 'passenger_email': 'guest@example.invalid',
                   'passenger_country_code': '+44', 'passenger_phone': '7700900123',
                   'booking_details': deepcopy(details if details is not None else {'note': 'synthetic'})}
        if ack is not None:
            payload['booking_terms_acknowledgement'] = deepcopy(ack)
        return client.post('/' + route + '/', payload, format='json')

    def pending(self, route='guest', **kwargs):
        response = self.checkout(route, **kwargs)
        self.assertEqual(response.status_code, 200, response.data)
        return PendingPayment.objects.get(pk=response.data['pending_payment_id'])

    def event(self, pending, *, event_type='payment_intent.succeeded', **pi_changes):
        pi = {'id': pending.payment_intent_id, 'status': 'succeeded', 'currency': 'gbp',
              'amount_received': 10001, 'amount': 10001,
              'metadata': {'pending_payment_id': str(pending.pk)}, 'charges': {'data': []}}
        pi.update(pi_changes)
        return {'id': 'evt_synthetic_checkout', 'object': 'event', 'type': event_type, 'data': {'object': pi}}

    def webhook(self, event, *, bad_signature=False):
        body = json.dumps(event).encode()
        timestamp = int(time.time())
        digest = hmac.new(SECRET.encode(), str(timestamp).encode() + b'.' + body, hashlib.sha256).hexdigest()
        if bad_signature:
            digest = '0' * 64
        return Client().post('/webhook/', body, content_type='application/json',
                             HTTP_STRIPE_SIGNATURE=f't={timestamp},v1={digest}')

    def assert_no_provider(self):
        self.create_intent.assert_not_called()
        self.modify_intent.assert_not_called()
        self.refund.assert_not_called()

    def test_guest_acceptance_committed_before_provider(self):
        pending = self.pending()
        observation = self.provider_observations[0]
        self.assertFalse(observation['inside_atomic'])
        self.assertIsNotNone(observation['record_id'])
        self.assertEqual(observation['snapshot']['accepted_at'], self.now.isoformat())
        self.assertEqual(observation['snapshot']['quoted_pence'], 10001)
        self.assertEqual(observation['snapshot']['policy_version'], CANDIDATE_POLICY_VERSION)
        self.assertEqual(pending.booking_details[TERMS_MARKER], {'required': True, 'schema': 1})
        self.assertEqual(self.create_intent.call_args.kwargs['amount'], 10001)

    def test_registered_acceptance_committed_before_provider(self):
        pending = self.pending('registered')
        self.assertEqual(pending.passenger_id, self.passenger.pk)
        self.assertFalse(self.provider_observations[0]['inside_atomic'])
        self.assertIsNotNone(self.provider_observations[0]['record_id'])

    def test_rollout_default_off_preserves_both_routes_and_strips_client_marker(self):
        with override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=False, ACT_BOOKING_TERMS_RELEASE=None):
            for route in ('guest', 'registered'):
                pending = self.pending(route, ack=None, details={TERMS_MARKER: {'required': True}, 'note': 'kept'})
                self.assertNotIn(TERMS_MARKER, pending.booking_details)
                self.assertEqual(pending.booking_details['note'], 'kept')
        self.assertFalse(BookingTermsAcceptance.objects.exists())
        self.assertTrue(all(x['record_id'] is None for x in self.provider_observations))

    def test_forged_required_false_cannot_opt_out(self):
        for route in ('guest', 'registered'):
            response = self.checkout(route, ack=None, details={TERMS_MARKER: {'required': False}})
            self.assertEqual(response.status_code, 400)
        self.assert_no_provider()

    def test_invalid_acknowledgements_block_both_routes(self):
        invalid = (None, {}, {**ACK, 'accepted': False}, {**ACK, 'accepted': 1},
                   {**ACK, 'terms_version': 'old'}, {**ACK, 'terms_sha256': 'b' * 64},
                   {**ACK, 'locale': 'ar'}, {**ACK, 'received_at': '2000-01-01'})
        for route in ('guest', 'registered'):
            for acknowledgement in invalid:
                with self.subTest(route=route, acknowledgement=acknowledgement):
                    self.assertEqual(self.checkout(route, ack=acknowledgement).status_code, 400)
        self.assert_no_provider()
        self.assertFalse(BookingTermsAcceptance.objects.exists())

    def test_unconfigured_unpublished_or_future_release_blocks_before_charge(self):
        releases = (None, {**RELEASE, 'published': False}, {**RELEASE, 'effective_at': '2099-01-01T00:00:00+00:00'})
        for release in releases:
            with self.subTest(release=release), override_settings(ACT_BOOKING_TERMS_RELEASE=release):
                self.assertEqual(self.checkout().status_code, 400)
        self.assert_no_provider()

    def test_wrong_document_hash_or_missing_locale_blocks_charge(self):
        for mode in ('hash', 'locale'):
            release = deepcopy(RELEASE)
            if mode == 'hash': release['locales']['en']['sha256'] = 'b' * 64
            else: release['locales'] = {}
            with self.subTest(mode=mode), override_settings(ACT_BOOKING_TERMS_RELEASE=release):
                self.assertEqual(self.checkout().status_code, 400)
        self.assert_no_provider()

    def test_malformed_flag_is_not_silently_disabled(self):
        with override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED='False'):
            self.assertGreaterEqual(self.checkout().status_code, 400)
        self.assert_no_provider()

    def test_registered_endpoint_keeps_existing_authentication(self):
        self.assertIn(self.checkout('registered', anonymous=True).status_code, (401, 403))
        self.assert_no_provider()

    def test_database_failure_prevents_payment_creation(self):
        with patch('apps.payments.checkout_terms.capture_checkout_terms', side_effect=DatabaseError('synthetic failure')):
            self.assertEqual(self.checkout().status_code, 500)
        self.assert_no_provider()

    def test_provider_failure_keeps_precharge_evidence_and_no_confirmed_trip(self):
        self.create_intent.side_effect = RuntimeError('synthetic provider unavailable')
        self.assertEqual(self.checkout().status_code, 500)
        self.assertEqual(BookingTermsAcceptance.objects.count(), 1)
        self.assertIsNone(PendingPayment.objects.get().payment_intent_id)
        self.assertFalse(Trip.objects.exists())
        self.queue.assert_not_called()

    def test_signed_guest_webhook_binds_and_keeps_snapshot_after_pending_deletion(self):
        pending = self.pending()
        record = BookingTermsAcceptance.objects.get(pending_payment=pending)
        snapshot = deepcopy(record.snapshot)
        self.assertEqual(self.webhook(self.event(pending)).status_code, 200)
        record.refresh_from_db()
        self.assertIsNone(record.pending_payment_id)
        self.assertEqual(record.snapshot, snapshot)
        self.assertEqual(record.trip_id, Trip.objects.get().pk)
        self.assertEqual(record.captured_pence, 10001)
        self.assertFalse(PendingPayment.objects.filter(pk=pending.pk).exists())
        self.assertTrue(record.trip.is_guest_checkout)

    def test_signed_registered_webhook_binds_correct_passenger(self):
        pending = self.pending('registered')
        self.assertEqual(self.webhook(self.event(pending)).status_code, 200)
        record = BookingTermsAcceptance.objects.get()
        self.assertEqual(record.trip.passenger_id, self.passenger.pk)
        self.assertFalse(record.trip.is_guest_checkout)

    def test_rollout_pause_does_not_lose_already_accepted_terms(self):
        pending = self.pending()
        with override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=False, ACT_BOOKING_TERMS_RELEASE=None):
            self.assertEqual(self.webhook(self.event(pending)).status_code, 200)
        self.assertIsNotNone(BookingTermsAcceptance.objects.get().trip_id)

    def test_legacy_checkout_not_assigned_new_terms_when_rollout_is_enabled(self):
        with override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=False): pending = self.pending(ack=None)
        self.assertEqual(self.webhook(self.event(pending)).status_code, 200)
        self.assertEqual(Trip.objects.count(), 1)
        self.assertFalse(BookingTermsAcceptance.objects.exists())

    def test_duplicate_signed_events_keep_one_booking_and_original_acceptance(self):
        pending = self.pending()
        event = self.event(pending)
        self.assertEqual(self.webhook(event).status_code, 200)
        before = deepcopy(BookingTermsAcceptance.objects.get().snapshot)
        self.assertEqual(self.webhook(event).status_code, 200)
        self.assertEqual(Trip.objects.count(), 1)
        self.assertEqual(BookingTermsAcceptance.objects.count(), 1)
        self.assertEqual(BookingTermsAcceptance.objects.get().snapshot, before)
        self.post_creation.assert_called_once()
        self.assertEqual(self.queue.call_count, 2)  # Existing idempotent task is requeued, never sent here.

    def test_missing_required_record_rolls_back_fulfillment(self):
        pending = self.pending()
        BookingTermsAcceptance.objects.all().delete()
        self.assertEqual(self.webhook(self.event(pending)).status_code, 500)
        self.assertTrue(PendingPayment.objects.filter(pk=pending.pk).exists())
        self.assertFalse(Trip.objects.exists())
        self.queue.assert_not_called()

    def test_corrupt_snapshot_rolls_back_fulfillment(self):
        pending = self.pending()
        record = BookingTermsAcceptance.objects.get()
        record.snapshot['terms_text'] = 'corrupt'; record.save(update_fields=['snapshot'])
        self.assertEqual(self.webhook(self.event(pending)).status_code, 500)
        self.assertTrue(PendingPayment.objects.filter(pk=pending.pk).exists())
        self.assertFalse(Trip.objects.exists())
        self.queue.assert_not_called()

    def test_mismatched_or_unsettled_provider_event_never_binds(self):
        pending = self.pending()
        for change in ({'amount_received': 1}, {'currency': 'usd'}, {'status': 'processing'},
                       {'amount_received': None}, {'id': 'pi_wrong'}):
            with self.subTest(change=change):
                self.assertEqual(self.webhook(self.event(pending, **change)).status_code, 500)
                self.assertFalse(Trip.objects.exists())
                self.assertIsNone(BookingTermsAcceptance.objects.get().trip_id)
        self.queue.assert_not_called()

    def test_unsigned_and_failed_events_do_not_confirm_booking(self):
        pending = self.pending()
        self.assertEqual(self.webhook(self.event(pending), bad_signature=True).status_code, 400)
        failed = self.event(pending, event_type='payment_intent.payment_failed', status='requires_payment_method')
        self.assertEqual(self.webhook(failed).status_code, 200)
        self.assertFalse(Trip.objects.exists())
        self.assertIsNone(BookingTermsAcceptance.objects.get().trip_id)
        self.queue.assert_not_called()

    def test_changed_priced_trip_cannot_reuse_original_acceptance(self):
        pending = self.pending()
        pending.trip_data['trip_time'] = '19:00:00'; pending.save(update_fields=['trip_data'])
        self.assertEqual(self.webhook(self.event(pending)).status_code, 500)
        self.assertFalse(Trip.objects.exists())
        self.assertTrue(PendingPayment.objects.filter(pk=pending.pk).exists())

    def test_duplicate_event_cannot_hide_missing_required_terms(self):
        pending = self.pending()
        event = self.event(pending)
        self.assertEqual(self.webhook(event).status_code, 200)
        BookingTermsAcceptance.objects.all().delete()
        self.assertEqual(self.webhook(event).status_code, 500)
        self.assertEqual(Trip.objects.count(), 1)
        self.assertFalse(BookingTermsAcceptance.objects.exists())

    def test_uk_pickup_resolves_unique_times_and_rejects_clock_change_ambiguity(self):
        self.assertEqual(_confirmed_pickup({'trip_date': '2027-06-01', 'trip_time': '10:00:00'}),
                         datetime(2027, 6, 1, 9, tzinfo=timezone.utc))
        for date in ('2027-03-28', '2027-10-31'):
            with self.subTest(date=date), self.assertRaises(ContractConflict):
                _confirmed_pickup({'trip_date': date, 'trip_time': '01:30:00'})

    def test_concurrent_signed_success_events_bind_only_once(self):
        pending = self.pending()
        event = self.event(pending)
        barrier = Barrier(2)
        def deliver():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.webhook(event).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: deliver(), range(2)))
        self.assertEqual(sorted(results), [200, 200])
        self.assertEqual(Trip.objects.count(), 1)
        self.assertEqual(BookingTermsAcceptance.objects.count(), 1)
        self.assertIsNotNone(BookingTermsAcceptance.objects.get().trip_id)
        self.assertFalse(PendingPayment.objects.filter(pk=pending.pk).exists())
        self.refund.assert_not_called()
