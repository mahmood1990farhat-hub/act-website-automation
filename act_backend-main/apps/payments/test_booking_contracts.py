"""Focused PostgreSQL storage tests. Synthetic records; no external provider calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import socket
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import connections, close_old_connections, transaction, IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TransactionTestCase, override_settings

from apps.payments.models import PendingPayment, BookingTermsAcceptance, CancellationReceipt, RefundReservation
from apps.payments.booking_contracts import (
    ContractConflict, PaymentObservation, capture_checkout_terms, bind_paid_terms,
    record_cancellation_receipt, prepare_refund_reservation, claim_refund_dispatch,
    record_provider_refund,
)
from apps.trips.models import Trip
from apps.trips.services.cancellation_policy import CANDIDATE_POLICY_VERSION

TEXT = 'SYNTHETIC TEST TERMS ONLY; not a published ACT document.'
HASH = hashlib.sha256(TEXT.encode()).hexdigest()
RELEASE = {'published': True, 'terms_version': 'test-only-v1',
           'policy_version': CANDIDATE_POLICY_VERSION, 'effective_at': '2026-01-01T00:00:00+00:00',
           'locales': {'en': {'text': TEXT, 'sha256': HASH, 'pdf_sha256': 'a' * 64,
                              'url': '/documents/en/test-only-v1.pdf'}}}
ACK = {'accepted': True, 'terms_version': 'test-only-v1', 'terms_sha256': HASH, 'locale': 'en'}


@override_settings(ACT_BOOKING_TERMS_RELEASE=RELEASE)
class BookingContractStorageTests(TransactionTestCase):
    def setUp(self):
        if connections['default'].vendor != 'postgresql':
            self.fail('These locking tests require PostgreSQL, not SQLite')
        self.now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        self.pickup = self.now + timedelta(hours=30)
        self.pending = PendingPayment.objects.create(
            price_breakdown={'total_cost': '100.01'},
            trip_data={'trip_date': self.pickup.date().isoformat(),
                       'trip_time': self.pickup.time().strftime('%H:%M:%S'), 'leg': 'outbound'},
            currency='GBP', expires_at=self.now + timedelta(minutes=15))
        # Application imports already completed; block accidental outbound calls during tests.
        original = socket.socket.connect
        def local_only(sock, address):
            if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
                raise AssertionError('External networking forbidden in storage tests')
            return original(sock, address)
        self.guard = patch('socket.socket.connect', local_only)
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def capture(self, **changes):
        args = dict(acknowledgement=deepcopy(ACK), locale='en', received_at=self.now,
                    confirmed_pickup_at=self.pickup)
        args.update(changes)
        return capture_checkout_terms(self.pending.pk, **args)

    def paid_trip(self, capture=True):
        record = self.capture() if capture else None
        self.pending.payment_intent_id = f'pi_synthetic{self.pending.pk}'
        self.pending.save(update_fields=['payment_intent_id'])
        trip = Trip.objects.create(pickup_lat=0, pickup_lng=0, dropoff_lat=1, dropoff_lng=1,
                                   trip_date=self.pickup.date(), trip_time=self.pickup.time().replace(tzinfo=None),
                                   passengers_count=1, cost=Decimal('100.01'), status='pending',
                                   stripe_payment_intent=self.pending.payment_intent_id, is_paid=True)
        bound = bind_paid_terms(self.pending.pk, trip.pk,
                               payment_intent_id=self.pending.payment_intent_id, captured_pence=10001)
        return trip, bound or record

    def context(self, hours=30, capture=True):
        trip, record = self.paid_trip(capture=capture)
        at = self.pickup - timedelta(hours=hours)
        receipt = record_cancellation_receipt(trip.pk, received_at=at)
        evidence = PaymentObservation(trip.stripe_payment_intent, 10001, 0, 0, at)
        return trip, record, receipt, evidence, at

    def prepared(self):
        trip, record, receipt, evidence, at = self.context()
        result, op = prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at)
        return trip, receipt, evidence, at, op

    def provider(self, op, status='succeeded', **changes):
        payload = {'id': 're_synthetic', 'amount': op.amount_pence, 'currency': 'gbp',
                   'payment_intent': op.payment_intent_id, 'status': status}
        payload.update(changes)
        return record_provider_refund(op.pk, provider_result=payload)

    def test_precharge_snapshot_and_repeat_acceptance_are_one_record(self):
        first = self.capture()
        second = self.capture(received_at=self.now + timedelta(seconds=5))
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.snapshot['accepted_at'], self.now.isoformat())
        self.assertEqual(BookingTermsAcceptance.objects.count(), 1)
        self.assertEqual(first.snapshot['quoted_pence'], 10001)
        self.assertEqual(first.snapshot['terms_text'], TEXT)

    def test_default_disabled_has_no_record(self):
        with override_settings(ACT_BOOKING_TERMS_RELEASE=None), self.assertRaises(ContractConflict):
            self.capture()
        self.assertEqual(BookingTermsAcceptance.objects.count(), 0)

    def test_unpublished_future_or_wrong_hash_release_is_blocked(self):
        for change in ({'published': False}, {'effective_at': '2099-01-01T00:00:00+00:00'},
                       {'policy_version': 'browser-invented'}):
            with self.subTest(change=change), override_settings(ACT_BOOKING_TERMS_RELEASE={**RELEASE, **change}), self.assertRaises(ContractConflict):
                self.capture()
        altered = deepcopy(RELEASE); altered['locales']['en']['sha256'] = 'b' * 64
        with override_settings(ACT_BOOKING_TERMS_RELEASE=altered), self.assertRaises(ContractConflict):
            self.capture()

    def test_forged_missing_or_false_acknowledgement_is_blocked(self):
        for ack in (None, {}, {**ACK, 'accepted': False}, {**ACK, 'accepted': 1},
                    {**ACK, 'terms_version': 'other'}, {**ACK, 'terms_sha256': 'b'*64},
                    {**ACK, 'policy_version': CANDIDATE_POLICY_VERSION}):
            with self.subTest(ack=ack), self.assertRaises(ContractConflict):
                self.capture(acknowledgement=ack)

    def test_locale_expiry_and_pickup_mismatch_are_blocked(self):
        for change in ({'locale': 'ar'}, {'received_at': self.now + timedelta(minutes=16)},
                       {'confirmed_pickup_at': self.pickup + timedelta(hours=1)}):
            with self.subTest(change=change), self.assertRaises(ContractConflict):
                self.capture(**change)

    def test_acceptance_cannot_be_invented_after_payment_started(self):
        self.pending.payment_intent_id = 'pi_already'; self.pending.save()
        with self.assertRaises(ContractConflict): self.capture()

    def test_acceptance_must_commit_before_external_payment_boundary(self):
        with transaction.atomic(), self.assertRaises(RuntimeError): self.capture()

    def test_existing_snapshot_cannot_be_repriced(self):
        first = self.capture()
        self.pending.price_breakdown = {'total_cost': '200.00'}; self.pending.save()
        with self.assertRaises(ContractConflict): self.capture()
        first.refresh_from_db(); self.assertEqual(first.snapshot['quoted_pence'], 10001)

    def test_paid_binding_survives_pending_deletion(self):
        trip, record = self.paid_trip()
        before = deepcopy(record.snapshot)
        self.pending.delete(); record.refresh_from_db()
        self.assertIsNone(record.pending_payment_id)
        self.assertEqual(record.trip_id, trip.pk)
        self.assertEqual(record.snapshot, before)
        self.assertEqual(record.captured_pence, 10001)
        with self.assertRaises(ProtectedError): trip.delete()

    def test_duplicate_binding_is_idempotent(self):
        trip, first = self.paid_trip()
        again = bind_paid_terms(self.pending.pk, trip.pk, payment_intent_id=trip.stripe_payment_intent,
                               captured_pence=10001)
        self.assertEqual(first.pk, again.pk)

    def test_wrong_provider_amount_or_identity_cannot_bind(self):
        trip, record = self.paid_trip()
        for pi, amount in [('pi_wrong', 10001), (trip.stripe_payment_intent, 1)]:
            with self.subTest(pi=pi, amount=amount), self.assertRaises(ContractConflict):
                bind_paid_terms(self.pending.pk, trip.pk, payment_intent_id=pi, captured_pence=amount)

    def test_legacy_booking_is_not_given_new_terms(self):
        trip, record, receipt, evidence, at = self.context(capture=False)
        self.assertIsNone(record)
        result, op = prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at)
        self.assertEqual(result['outcome'], 'accepted_terms_review_required'); self.assertIsNone(op)
        self.assertEqual(BookingTermsAcceptance.objects.count(), 0)

    def test_snapshot_corruption_blocks_assessment(self):
        trip, record, receipt, evidence, at = self.context()
        record.snapshot['quoted_pence'] = 1; record.save(update_fields=['snapshot'])
        with self.assertRaises(ContractConflict):
            prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at)

    def test_receipt_retries_preserve_first_timestamp(self):
        trip, record = self.paid_trip()
        first = record_cancellation_receipt(trip.pk, received_at=self.now)
        again = record_cancellation_receipt(trip.pk, received_at=self.now + timedelta(hours=10))
        self.assertEqual(first.pk, again.pk); self.assertEqual(again.received_at, self.now)
        trip.refresh_from_db(); self.assertEqual(trip.status, 'pending')

    def test_receipt_reason_or_earlier_evidence_requires_review(self):
        trip, record = self.paid_trip(); record_cancellation_receipt(trip.pk, received_at=self.now)
        for at, kind in [(self.now, 'no_show'), (self.now - timedelta(seconds=1), 'passenger_cancellation')]:
            with self.assertRaises(ContractConflict): record_cancellation_receipt(trip.pk, received_at=at, kind=kind)

    def test_full_refund_reservation_reuses_one_key(self):
        trip, receipt, evidence, at, first = self.prepared()
        result, again = prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at)
        self.assertEqual(first.pk, again.pk); self.assertEqual(first.idempotency_key, again.idempotency_key)
        self.assertEqual(first.amount_pence, 10001); self.assertEqual(RefundReservation.objects.count(), 1)

    def test_half_or_zero_schedule_without_loss_review_does_not_reserve(self):
        trip, record, receipt, evidence, at = self.context(hours=24)
        result, op = prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at)
        self.assertTrue(result['review_required']); self.assertIsNone(op)
        self.assertEqual(result['standard_refund_percent'], 50)

    def test_staff_review_allows_capped_partial_reservation(self):
        trip, record, receipt, evidence, at = self.context(hours=24)
        reviewer = get_user_model().objects.create(username='synthetic-reviewer', is_staff=True, is_active=True)
        result, op = prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at,
                          reviewed_loss_pence=5000, review_reference='synthetic-review-1', reviewer_id=reviewer.pk)
        self.assertEqual(op.amount_pence, 5001)
        self.assertEqual(op.assessment['reviewer_id'], str(reviewer.pk))

    def test_nonstaff_cannot_supply_loss_review(self):
        trip, record, receipt, evidence, at = self.context(hours=12)
        reviewer = get_user_model().objects.create(username='synthetic-passenger', is_staff=False, is_active=True)
        with self.assertRaises(ContractConflict):
            prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at,
                reviewed_loss_pence=10001, review_reference='synthetic', reviewer_id=reviewer.pk)

    def test_pending_disputed_stale_or_wrong_payment_blocks_reservation(self):
        trip, record, receipt, evidence, at = self.context()
        for change in ({'pending_pence': 1}, {'disputed': True}, {'settled': False},
                       {'observed_at': at - timedelta(minutes=6)}, {'payment_intent_id': 'pi_wrong'}):
            with self.subTest(change=change), self.assertRaises(ContractConflict):
                prepare_refund_reservation(receipt.pk, evidence=replace(evidence, **change), assessed_at=at)

    def test_changed_refund_balance_cannot_dispatch_stale_reservation(self):
        trip, receipt, evidence, at, op = self.prepared()
        with self.assertRaises(ContractConflict):
            claim_refund_dispatch(op.pk, evidence=replace(evidence, refunded_pence=1), claimed_at=at)
        op.refresh_from_db(); self.assertEqual(op.status, 'prepared')

    def test_claim_commits_once_and_does_not_auto_retry_after_timeout(self):
        trip, receipt, evidence, at, op = self.prepared()
        first = claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at)
        self.assertEqual(first['amount'], 10001); self.assertEqual(first['idempotency_key'], op.idempotency_key)
        self.assertIsNone(claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at + timedelta(hours=25)))
        op.refresh_from_db(); self.assertEqual(op.status, 'in_flight'); self.assertEqual(op.first_attempt_at, at)

    def test_claim_cannot_return_inside_uncommitted_outer_transaction(self):
        trip, receipt, evidence, at, op = self.prepared()
        with transaction.atomic(), self.assertRaises(RuntimeError):
            claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at)
        op.refresh_from_db(); self.assertEqual(op.status, 'prepared')

    def test_pending_provider_result_is_not_success_and_duplicate_events_do_not_regress(self):
        trip, receipt, evidence, at, op = self.prepared()
        claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at)
        self.assertEqual(self.provider(op, 'pending').status, 'pending')
        self.assertIsNone(claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at))
        self.assertEqual(self.provider(op).status, 'succeeded')
        self.assertEqual(self.provider(op, 'pending').status, 'succeeded')
        self.assertEqual(self.provider(op).status, 'succeeded')

    def test_failed_refund_stays_reserved_without_new_payment_attempt(self):
        trip, receipt, evidence, at, op = self.prepared()
        claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at)
        self.assertEqual(self.provider(op, 'failed').status, 'failed')
        self.assertIsNone(claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at))
        with self.assertRaises(ContractConflict): self.provider(op, 'succeeded')

    def test_provider_identity_amount_and_currency_must_match(self):
        trip, receipt, evidence, at, op = self.prepared()
        claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at)
        for change in ({'amount': 1}, {'amount': True}, {'currency': 'usd'}, {'payment_intent': 'pi_wrong'}, {'id': ''}):
            with self.subTest(change=change), self.assertRaises(ContractConflict): self.provider(op, **change)

    def test_database_rejects_zero_reservation(self):
        trip, record, receipt, evidence, at = self.context()
        with self.assertRaises(IntegrityError), transaction.atomic():
            RefundReservation.objects.create(receipt=receipt, payment_intent_id='pi_synthetic', amount_pence=0, assessment={})

    def race(self, call):
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return call()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            return [f.result(timeout=20) for f in futures]

    def test_postgres_concurrent_receipts_create_one_row(self):
        trip, record = self.paid_trip()
        values = self.race(lambda: record_cancellation_receipt(trip.pk, received_at=self.now).pk)
        self.assertEqual(values[0], values[1]); self.assertEqual(CancellationReceipt.objects.count(), 1)

    def test_postgres_concurrent_reservations_create_one_row(self):
        trip, record, receipt, evidence, at = self.context()
        values = self.race(lambda: prepare_refund_reservation(receipt.pk, evidence=evidence, assessed_at=at)[1].pk)
        self.assertEqual(values[0], values[1]); self.assertEqual(RefundReservation.objects.count(), 1)

    def test_postgres_concurrent_dispatch_claims_only_once(self):
        trip, receipt, evidence, at, op = self.prepared()
        values = self.race(lambda: claim_refund_dispatch(op.pk, evidence=evidence, claimed_at=at))
        self.assertEqual(sum(x is not None for x in values), 1)
