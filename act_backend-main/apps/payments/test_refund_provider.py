"""Real PostgreSQL reservation tests with mocked Stripe and signed synthetic events.
No production data, credentials, payment, email or off-origin network requests.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import hmac
import json
from threading import Barrier
import time
from unittest.mock import patch

from django.db import close_old_connections, connection, transaction
from django.test import RequestFactory, TransactionTestCase, override_settings

from apps.payments import test_booking_contracts as fixtures
from apps.payments import refund_provider as provider
from apps.payments.booking_contracts import ContractConflict, claim_refund_dispatch
from apps.payments.models import RefundReservation
from apps.payments.views.views import stripe_webhook_view


@override_settings(ACT_BOOKING_TERMS_RELEASE=fixtures.RELEASE,
                   ACT_REFUND_PROVIDER_ENABLED=True, ACT_REFUND_DISPATCH_ENABLED=True,
                   ACT_REFUND_PROVIDER_LIVEMODE=False, STRIPE_SECRET_KEY='sk_test_synthetic',
                   STRIPE_WEBHOOK_SECRET='whsec_synthetic_provider')
class RefundProviderTests(TransactionTestCase):
    # Reuse only synthetic fixture helpers, not their previously completed tests.
    capture = fixtures.BookingContractStorageTests.capture
    paid_trip = fixtures.BookingContractStorageTests.paid_trip
    context = fixtures.BookingContractStorageTests.context
    prepared = fixtures.BookingContractStorageTests.prepared

    def setUp(self):
        fixtures.BookingContractStorageTests.setUp(self)
        self.trip, self.receipt, self.evidence, self.at, self.operation = self.prepared()
        self.rows = []
        self.payment_changes = {}
        self.charge_changes = {}
        self.create_status = 'succeeded'
        self.mock_now = self.enterContext(patch.object(provider.timezone, 'now', return_value=self.at))
        self.pi = self.enterContext(patch.object(provider.stripe.PaymentIntent, 'retrieve', side_effect=self.payment))
        self.charge = self.enterContext(patch.object(provider.stripe.Charge, 'retrieve', side_effect=lambda *a, **k: self.payment()['latest_charge']))
        self.listed = self.enterContext(patch.object(provider.stripe.Refund, 'list', side_effect=self.refund_page))
        self.retrieved = self.enterContext(patch.object(provider.stripe.Refund, 'retrieve', side_effect=self.retrieve_refund))
        self.created = self.enterContext(patch.object(provider.stripe.Refund, 'create', side_effect=self.create_refund))

    def payment(self, *args, **kwargs):
        charge = {'id': 'ch_synthetic', 'object': 'charge',
                  'payment_intent': self.trip.stripe_payment_intent,
                  'currency': 'gbp', 'livemode': False, 'paid': True, 'captured': True,
                  'status': 'succeeded', 'amount_captured': 10001,
                  'amount_refunded': sum(r['amount'] for r in self.rows if r['status'] == 'succeeded'),
                  'disputed': False, **self.charge_changes}
        return deepcopy({'id': self.trip.stripe_payment_intent, 'object': 'payment_intent',
                         'livemode': False, 'status': 'succeeded', 'currency': 'gbp',
                         'amount_received': 10001, 'latest_charge': charge, **self.payment_changes})

    def refund_page(self, **kwargs):
        return {'object': 'list', 'data': deepcopy(self.rows), 'has_more': False}

    def refund(self, **changes):
        return {'id': 're_synthetic', 'object': 'refund', 'charge': 'ch_synthetic',
                'payment_intent': self.trip.stripe_payment_intent, 'currency': 'gbp',
                'amount': self.operation.amount_pence, 'status': self.create_status,
                'metadata': {'act_refund_operation': str(self.operation.pk)}, **changes}

    def create_refund(self, **kwargs):
        self.assertFalse(connection.in_atomic_block)
        self.operation.refresh_from_db()
        self.assertEqual(self.operation.status, 'in_flight')
        self.assertIsNotNone(self.operation.first_attempt_at)
        self.assertEqual(kwargs['amount'], self.operation.amount_pence)
        self.assertEqual(kwargs['payment_intent'], self.trip.stripe_payment_intent)
        self.assertEqual(kwargs['idempotency_key'], self.operation.idempotency_key)
        self.assertEqual(kwargs['api_key'], 'sk_test_synthetic')
        row = self.refund(); self.rows.append(row)
        return deepcopy(row)

    def retrieve_refund(self, refund_id, **kwargs):
        return deepcopy(next(row for row in self.rows if row['id'] == refund_id))

    def dispatch(self):
        return provider.dispatch_reserved_refund(self.operation.pk)

    def claim(self):
        return claim_refund_dispatch(self.operation.pk, evidence=self.evidence, claimed_at=self.at)

    def event(self, **changes):
        return {'id': 'evt_synthetic', 'object': 'event', 'type': 'refund.updated',
                'livemode': False, 'data': {'object': self.refund()}, **changes}

    def webhook(self, event, valid=True):
        raw = json.dumps(event).encode()
        ts = str(int(time.time()))
        sig = hmac.new(b'whsec_synthetic_provider', ts.encode()+b'.'+raw, hashlib.sha256).hexdigest()
        request = RequestFactory().post('/api/payments/webhook/', data=raw, content_type='application/json',
                     HTTP_STRIPE_SIGNATURE=f't={ts},v1={sig if valid else "invalid"}')
        return stripe_webhook_view(request)

    def test_default_read_and_dispatch_gates_stop_before_provider(self):
        for overrides in ({'ACT_REFUND_PROVIDER_ENABLED': False},
                          {'ACT_REFUND_PROVIDER_ENABLED': 'True'},
                          {'ACT_REFUND_DISPATCH_ENABLED': False}):
            with self.subTest(overrides=overrides), override_settings(**overrides), self.assertRaises(ContractConflict):
                self.dispatch()
        self.created.assert_not_called(); self.pi.assert_not_called()

    def test_mode_mismatch_and_transaction_are_rejected(self):
        with override_settings(STRIPE_SECRET_KEY='sk_live_not_allowed'), self.assertRaises(ContractConflict): self.dispatch()
        with transaction.atomic(), self.assertRaises(ContractConflict): self.dispatch()
        self.pi.assert_not_called(); self.created.assert_not_called()

    def test_provider_payment_validation_precedes_claim(self):
        for change in ({'livemode': True}, {'currency': 'usd'}, {'status': 'requires_capture'},
                       {'amount_received': True}, {'amount_received': 10000},
                       {'id': 'pi_wrong'}, {'transfer_data': {'destination': 'acct_other'}}):
            with self.subTest(change=change):
                self.payment_changes = change
                with self.assertRaises(ContractConflict): self.dispatch()
        self.created.assert_not_called()
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'prepared')

    def test_capture_charge_and_dispute_checks(self):
        for change in ({'paid': False}, {'captured': False}, {'payment_intent': 'pi_other'},
                       {'currency': 'usd'}, {'amount_captured': -1}, {'livemode': True}, {'disputed': True}):
            with self.subTest(change=change):
                self.charge_changes = change
                with self.assertRaises(ContractConflict): self.dispatch()
        self.created.assert_not_called()

    def test_full_observation_paginates_and_includes_pending(self):
        a = self.refund(id='re_first', amount=1000, metadata={})
        b = self.refund(id='re_second', amount=500, status='pending', metadata={})
        self.rows = [a, b]
        self.listed.side_effect = [dict(object='list', data=[a], has_more=True),
                                 dict(object='list', data=[b], has_more=False)]
        evidence = provider.observe_payment(self.trip.stripe_payment_intent)
        self.assertEqual((evidence.refunded_pence, evidence.pending_pence), (1000, 500))
        self.assertEqual(self.listed.call_args_list[1].kwargs['starting_after'], 're_first')
        self.assertEqual(self.listed.call_args_list[0].kwargs['limit'], 100)

    def test_incomplete_duplicate_wrong_identity_history_is_rejected(self):
        for page in (dict(object='list', data=[], has_more=True),
                     dict(object='list', data=[self.refund(), self.refund()], has_more=False),
                     dict(object='list', data=[self.refund(payment_intent='pi_other')], has_more=False),
                     dict(object='list', data=[self.refund(amount=0)], has_more=False)):
            with self.subTest(page=page):
                self.listed.side_effect = None; self.listed.return_value = page
                with self.assertRaises(ContractConflict): provider.observe_payment(self.trip.stripe_payment_intent)
        self.created.assert_not_called()

    def test_page_limit_holds_instead_of_truncating(self):
        counter = iter(range(10))
        self.listed.side_effect = lambda **k: dict(object='list', has_more=True,
                                                  data=[self.refund(id=f're_page{next(counter)}', amount=1)])
        with self.assertRaises(ContractConflict): provider.observe_payment(self.trip.stripe_payment_intent)
        self.assertEqual(self.listed.call_count, 10)

    def test_balance_change_between_reads_holds(self):
        first = self.payment(); last = deepcopy(first); last['latest_charge']['amount_refunded'] = 1
        self.pi.side_effect = [first, last]
        with self.assertRaises(ContractConflict): self.dispatch()
        self.created.assert_not_called()

    def test_inconsistent_charge_total_holds(self):
        self.charge_changes['amount_refunded'] = 1
        with self.assertRaises(ContractConflict): self.dispatch()
        self.created.assert_not_called()

    def test_pending_or_external_refund_blocks_prepared_amount(self):
        for status in ('pending', 'requires_action', 'succeeded'):
            with self.subTest(status=status):
                self.rows = [self.refund(id='re_external', amount=100, status=status, metadata={})]
                with self.assertRaises(ContractConflict): self.dispatch()
        self.created.assert_not_called()

    def test_explicit_amount_stable_key_and_committed_claim(self):
        # Genuine partial reservation, using the approved reviewed-loss service.
        self.operation.delete()
        from apps.payments.booking_contracts import prepare_refund_reservation
        from django.contrib.auth import get_user_model
        self.at = self.pickup - timedelta(hours=18)
        self.evidence = replace(self.evidence, observed_at=self.at)
        self.mock_now.return_value = self.at
        self.receipt.received_at = self.at; self.receipt.save()
        reviewer = get_user_model().objects.create(email='reviewer@example.invalid', is_active=True, is_staff=True)
        _, self.operation = prepare_refund_reservation(self.receipt.pk, evidence=self.evidence,
            assessed_at=self.at, reviewed_loss_pence=5000, review_reference='synthetic-review', reviewer_id=reviewer.pk)
        self.assertEqual(self.operation.amount_pence, 5001)
        self.assertEqual(self.dispatch()['status'], 'succeeded')
        self.dispatch(); self.created.assert_called_once()
        self.assertEqual(self.created.call_args.kwargs['amount'], 5001)

    def test_pending_failed_requires_action_are_not_success(self):
        self.create_status = 'pending'
        self.assertEqual(self.dispatch()['status'], 'pending')
        self.rows[0]['status'] = 'requires_action'
        self.assertEqual(provider.reconcile_reserved_refund(self.operation.pk)['status'], 'requires_action')
        self.rows[0]['status'] = 'failed'
        self.assertEqual(provider.reconcile_reserved_refund(self.operation.pk)['status'], 'failed')
        self.dispatch(); self.created.assert_called_once()

    def test_timeout_keeps_claim_and_does_not_retry_after_key_retention(self):
        self.created.side_effect = TimeoutError('synthetic timeout; never log full error')
        self.assertEqual(self.dispatch()['status'], 'reconcile')
        self.mock_now.return_value = self.at + timedelta(days=3)
        self.assertEqual(self.dispatch()['status'], 'reconcile')
        self.created.assert_called_once()
        self.assertEqual(provider.reconcile_reserved_refund(self.operation.pk)['status'], 'reconcile')
        self.created.assert_called_once()

    def test_timeout_can_be_recovered_by_metadata_without_new_refund(self):
        def timeout(**kwargs):
            self.create_refund(**kwargs)
            raise TimeoutError('lost response')
        self.created.side_effect = timeout
        self.assertEqual(self.dispatch()['status'], 'reconcile')
        self.assertEqual(provider.reconcile_reserved_refund(self.operation.pk)['status'], 'succeeded')
        self.created.assert_called_once()

    def test_webhook_winning_timeout_race_is_not_overwritten(self):
        def race(**kwargs):
            self.create_refund(**kwargs)
            self.assertEqual(provider.handle_verified_refund_event(self.event())['status'], 'succeeded')
            raise TimeoutError('response lost after webhook')
        self.created.side_effect = race
        self.assertEqual(self.dispatch()['status'], 'succeeded')
        self.created.assert_called_once()

    def test_malformed_create_response_is_held(self):
        self.created.side_effect = lambda **k: self.refund(amount=1)
        self.assertEqual(self.dispatch()['status'], 'reconcile')
        self.dispatch(); self.created.assert_called_once()

    def test_unattempted_reconciliation_is_blocked(self):
        with self.assertRaises(ContractConflict): provider.reconcile_reserved_refund(self.operation.pk)
        self.retrieved.assert_not_called(); self.listed.assert_not_called()

    def test_multiple_operation_matches_need_manual_reconciliation(self):
        self.claim()
        self.rows = [self.refund(id='re_one', amount=10), self.refund(id='re_two', amount=10)]
        with self.assertRaises(ContractConflict): provider.reconcile_reserved_refund(self.operation.pk)
        self.created.assert_not_called()

    def test_known_refund_identity_currency_amount_and_marker_are_checked(self):
        self.create_status = 'pending'; self.dispatch()
        original = deepcopy(self.rows[0])
        for change in ({'amount': 1}, {'currency': 'usd'}, {'payment_intent': 'pi_other'},
                       {'metadata': {}}, {'charge': 'ch_other'}, {'id': 're_different'}):
            with self.subTest(change=change):
                self.rows = [{**original, **change}]
                # A retrieve response can differ from its requested id; do not trust it.
                self.retrieved.side_effect = None; self.retrieved.return_value = self.rows[0]
                with self.assertRaises(ContractConflict): provider.reconcile_reserved_refund(self.operation.pk)
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'pending')
        self.created.assert_called_once()

    def test_concurrent_dispatch_calls_create_only_once(self):
        barrier = Barrier(2); observe = provider.observe_payment
        def together(payment_id):
            result = observe(payment_id); barrier.wait(timeout=10); return result
        def dispatch_thread():
            close_old_connections()
            try: return self.dispatch()
            finally: close_old_connections()
        with patch.object(provider, 'observe_payment', side_effect=together), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: dispatch_thread(), range(2)))
        self.created.assert_called_once()
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'succeeded')
        self.assertEqual(len(results), 2)

    def test_invalid_signature_does_not_reconcile(self):
        with patch.object(provider, 'reconcile_reserved_refund') as reconcile:
            self.assertEqual(self.webhook(self.event(), valid=False).status_code, 400)
        reconcile.assert_not_called()

    def test_signed_event_uses_current_provider_state_not_old_payload(self):
        self.create_status = 'pending'; self.dispatch(); self.rows[0]['status'] = 'succeeded'
        old = self.event(data={'object': self.refund(status='pending')})
        self.assertEqual(self.webhook(old).status_code, 200)
        self.assertEqual(self.webhook(old).status_code, 200)
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'succeeded')
        self.created.assert_called_once()

    def test_signed_wrong_mode_account_or_payment_is_non_success(self):
        self.claim(); self.rows = [self.refund()]
        for changes in ({'livemode': True}, {'account': 'acct_other'},
                        {'data': {'object': self.refund(payment_intent='pi_other')}}):
            with self.subTest(changes=changes):
                self.assertEqual(self.webhook(self.event(**changes)).status_code, 500)
        self.created.assert_not_called()

    def test_unknown_external_refund_is_not_adopted(self):
        event = self.event(data={'object': self.refund(id='re_external', metadata={})})
        self.assertEqual(self.webhook(event).status_code, 200)
        self.retrieved.assert_not_called(); self.listed.assert_not_called()
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'prepared')

    def test_provider_read_failure_returns_non_success_for_webhook_retry(self):
        self.claim(); self.pi.side_effect = TimeoutError('synthetic read unavailable')
        self.assertEqual(self.webhook(self.event()).status_code, 500)
        self.created.assert_not_called()

    def test_disabled_event_handling_does_not_read_provider_or_change_state(self):
        with override_settings(ACT_REFUND_PROVIDER_ENABLED=False):
            self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.pi.assert_not_called(); self.created.assert_not_called()
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'prepared')

    def test_conflicting_terminal_provider_status_is_not_silently_rewritten(self):
        self.dispatch(); self.rows[0]['status'] = 'failed'
        self.assertEqual(provider.reconcile_reserved_refund(self.operation.pk)['status'], 'reconcile')
        self.assertEqual(provider.reconcile_reserved_refund(self.operation.pk)['status'], 'reconcile')
        self.operation.refresh_from_db(); self.assertEqual(self.operation.status, 'reconcile')
        self.created.assert_called_once()

    def test_payment_events_keep_existing_handler(self):
        with patch('apps.payments.views.views.handle_payment_failed') as failed:
            event = {'id': 'evt_payment', 'object': 'event', 'type': 'payment_intent.payment_failed',
                     'data': {'object': {'id': 'pi_synthetic', 'metadata': {}}}, 'livemode': False}
            self.assertEqual(self.webhook(event).status_code, 200)
            failed.assert_called_once()
        self.created.assert_not_called()
