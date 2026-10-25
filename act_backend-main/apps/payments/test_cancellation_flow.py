"""Routed cancellation/review tests, PostgreSQL locks/trigger and mocked provider.
Only synthetic records. All outbound network connections are blocked by fixtures.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection, close_old_connections, transaction, IntegrityError
from django.test import TransactionTestCase, override_settings
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.payments import test_booking_contracts as fixture
from apps.payments import test_refund_provider as provider_fixture
from apps.payments import refund_provider as provider
from apps.payments.booking_contracts import ContractConflict, record_provider_refund
from apps.payments.cancellation_flow import (
    stop_passenger_journey, process_stopped_case, finalize_managed_refund, public_outcome,
)
from apps.payments.cancellation_views import (
    PassengerCancelTripView, LegacyCancelView, CancellationReviewView, CancellationReconcileView,
)
from apps.payments.models import BookingTermsAcceptance, CancellationReceipt, CancellationCase, RefundReservation, RefundPosting
from apps.passengers.models import Passenger
from apps.trips.models import Trip
from apps.earnings.models import CompanyRefundLedger


@override_settings(ACT_BOOKING_TERMS_RELEASE=fixture.RELEASE,
                   ACT_CANCELLATION_FLOW_ENABLED=True,
                   ACT_REFUND_PROVIDER_ENABLED=True, ACT_REFUND_DISPATCH_ENABLED=True,
                   ACT_REFUND_PROVIDER_LIVEMODE=False, STRIPE_SECRET_KEY='sk_test_synthetic',
                   STRIPE_WEBHOOK_SECRET='whsec_synthetic_provider')
class CancellationFlowTests(TransactionTestCase):
    capture = fixture.BookingContractStorageTests.capture
    paid_trip = fixture.BookingContractStorageTests.paid_trip
    payment = provider_fixture.RefundProviderTests.payment
    refund_page = provider_fixture.RefundProviderTests.refund_page
    refund = provider_fixture.RefundProviderTests.refund
    retrieve_refund = provider_fixture.RefundProviderTests.retrieve_refund
    event = provider_fixture.RefundProviderTests.event
    webhook = provider_fixture.RefundProviderTests.webhook

    def setUp(self):
        fixture.BookingContractStorageTests.setUp(self)
        self.trip, self.terms = self.paid_trip()
        self.user = get_user_model().objects.create(
            email='passenger@example.invalid', username='synthetic-passenger',
            account_type='passenger', is_profile_completed=True, is_admin_verified=True)
        self.passenger = Passenger.objects.create(user=self.user)
        self.trip.passenger = self.passenger
        self.trip.passenger_email = self.user.email
        self.trip.save(update_fields=['passenger', 'passenger_email'])
        self.staff = get_user_model().objects.create(email='reviewer@example.invalid',
            username='synthetic-reviewer', is_staff=True, is_active=True)
        self.staff.user_permissions.add(Permission.objects.get(
            content_type__app_label='payments', codename='review_cancellationcase'))
        self.rows, self.payment_changes, self.charge_changes = [], {}, {}
        self.create_status = 'succeeded'
        self.at = self.now
        self.clock = self.enterContext(patch.object(provider.timezone, 'now', side_effect=lambda: self.at))
        self.pi = self.enterContext(patch.object(provider.stripe.PaymentIntent, 'retrieve', side_effect=self.payment))
        self.enterContext(patch.object(provider.stripe.Charge, 'retrieve', side_effect=lambda *a, **k: self.payment()['latest_charge']))
        self.listed = self.enterContext(patch.object(provider.stripe.Refund, 'list', side_effect=self.refund_page))
        self.enterContext(patch.object(provider.stripe.Refund, 'retrieve', side_effect=self.retrieve_refund))
        self.created = self.enterContext(patch.object(provider.stripe.Refund, 'create', side_effect=self.create_refund))
        self.tracking = self.enterContext(patch('apps.trips.services.trip_tracking.stop_trip_tracking'))

    def create_refund(self, **kwargs):
        self.operation = RefundReservation.objects.get(receipt__trip=self.trip)
        fresh = Trip.objects.get(pk=self.trip.pk)
        self.assertEqual(fresh.status, 'cancelled')
        self.assertTrue(CancellationCase.objects.filter(receipt__trip=fresh).exists())
        self.assertFalse(connection.in_atomic_block)
        return provider_fixture.RefundProviderTests.create_refund(self, **kwargs)

    def call(self, cls, *, user=None, payload=None, receipt_id=None):
        request = APIRequestFactory().post('/synthetic/', data=payload or {}, format='json')
        force_authenticate(request, user=user or self.user)
        kwargs = {'receipt_id': receipt_id} if receipt_id else {'trip_id': self.trip.pk}
        return cls.as_view()(request, **kwargs)

    def cancel(self, **kwargs):
        return self.call(PassengerCancelTripView, **kwargs)

    def review(self, loss=5000, **kwargs):
        return self.call(CancellationReviewView, user=self.staff,
            receipt_id=self.case().pk,
            payload={'reviewed_net_loss_pence': loss, 'review_reference': 'synthetic-evidence-001'}, **kwargs)

    def case(self):
        return CancellationCase.objects.get(receipt__trip=self.trip)

    def op(self):
        return RefundReservation.objects.get(receipt__trip=self.trip)

    def near(self, hours):
        self.at = self.pickup - timedelta(hours=hours)

    def test_both_existing_urls_point_to_managed_view(self):
        from apps.trips.urls import urlpatterns as trips
        from apps.trips.passenger_urls import urlpatterns as passengers
        for patterns in (trips, passengers):
            route = next(p for p in patterns if str(p.pattern).endswith('/cancel/'))
            self.assertIs(route.callback.view_class, PassengerCancelTripView)

    def test_full_refund_stops_before_money_and_posts_once(self):
        response = self.cancel()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['refund_processed'])
        self.assertEqual(response.data['data']['refund_amount'], '100.01')
        self.assertEqual((CancellationReceipt.objects.count(), RefundReservation.objects.count(), RefundPosting.objects.count()), (1, 1, 1))
        self.assertEqual(CompanyRefundLedger.objects.get().refund_amount, Decimal('-100.01'))
        self.tracking.assert_called_once()
        self.assertIn('no-store', response.get('Cache-Control', ''))

    def test_duplicate_cancellation_never_refunds_or_posts_twice(self):
        first, second = self.cancel(), self.cancel()
        self.assertEqual(first.data['data']['cancellation_id'], second.data['data']['cancellation_id'])
        self.created.assert_called_once()
        self.assertEqual(CompanyRefundLedger.objects.count(), 1)

    def test_partial_standard_requires_authorised_evidence(self):
        self.near(20)
        response = self.cancel()
        self.assertTrue(response.data['data']['review_required'])
        self.assertEqual(response.data['data']['standard_refund_percent'], 50)
        self.created.assert_not_called()
        result = self.review()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.created.call_args.kwargs['amount'], 5001)
        self.assertEqual(CompanyRefundLedger.objects.get().refund_amount, Decimal('-50.01'))

    def test_exact12_no_refund_needs_review_then_persists_zero(self):
        self.near(12)
        self.assertTrue(self.cancel().data['data']['review_required'])
        result = self.review(loss=10001)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(self.case().decision['final'])
        self.assertEqual(result.data['data']['refund_status'], 'not_due')
        self.assertEqual(RefundReservation.objects.count(), 0)
        self.created.assert_not_called()

    def test_zero_loss_refunds_full_in_late_band(self):
        self.near(8); self.cancel()
        self.assertEqual(self.review(loss=0).status_code, 200)
        self.assertEqual(self.created.call_args.kwargs['amount'], 10001)

    def test_staff_without_specific_permission_cannot_review(self):
        self.near(20); self.cancel(); self.pi.reset_mock()
        other = get_user_model().objects.create(email='unprivileged@example.invalid', is_staff=True)
        result = self.call(CancellationReviewView, user=other, receipt_id=self.case().pk,
            payload={'reviewed_net_loss_pence': 1, 'review_reference': 'synthetic-evidence'})
        self.assertEqual(result.status_code, 403)
        self.pi.assert_not_called(); self.created.assert_not_called()

    def test_passenger_and_inactive_staff_cannot_review(self):
        self.near(20); self.cancel()
        for user in (self.user, self.staff):
            if user.is_staff:
                user.is_active = False; user.save(update_fields=['is_active'])
            result = self.call(CancellationReviewView, user=user, receipt_id=self.case().pk)
            self.assertEqual(result.status_code, 403)
        self.created.assert_not_called()

    def test_forged_review_and_invalid_loss_rejected_before_provider(self):
        self.near(20); self.cancel(); self.pi.reset_mock()
        for payload in ({'reviewed_net_loss_pence': True, 'review_reference': 'synthetic-evidence'},
                        {'reviewed_net_loss_pence': -1, 'review_reference': 'synthetic-evidence'},
                        {'reviewed_net_loss_pence': 10, 'review_reference': ''},
                        {'reviewed_net_loss_pence': 10, 'review_reference': 'synthetic-evidence', 'reviewer_id': self.staff.pk}):
            result = self.call(CancellationReviewView, user=self.staff, receipt_id=self.case().pk, payload=payload)
            self.assertEqual(result.status_code, 409)
        self.pi.assert_not_called(); self.created.assert_not_called()

    def test_another_passenger_cannot_cancel_even_matching_contact_email(self):
        other = get_user_model().objects.create(email='other@example.invalid', account_type='passenger',
            is_profile_completed=True, is_admin_verified=True)
        Passenger.objects.create(user=other)
        self.trip.passenger_email = other.email; self.trip.save(update_fields=['passenger_email'])
        response = self.cancel(user=other)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(CancellationReceipt.objects.count(), 0)
        self.created.assert_not_called()

    def test_guest_email_match_uses_same_managed_path(self):
        self.trip.passenger = None; self.trip.save(update_fields=['passenger'])
        self.assertEqual(self.cancel().status_code, 200)
        self.created.assert_called_once()

    def test_client_cannot_supply_refund_amount_time_or_kind(self):
        self.near(20)
        response = self.cancel(payload={'refund_amount': 10001, 'cancellation_kind': 'act_unable_to_supply',
                                       'received_at': '2000-01-01T00:00:00Z', 'reviewed_net_loss_pence': 0})
        self.assertTrue(response.data['data']['review_required'])
        self.assertEqual(self.case().receipt.received_at, self.at)
        self.assertEqual(self.case().receipt.kind, 'passenger_cancellation')
        self.created.assert_not_called()

    def test_provider_outage_does_not_undo_cancellation(self):
        self.pi.side_effect = RuntimeError('synthetic offline')
        response = self.cancel()
        self.assertEqual(response.status_code, 200)
        self.trip.refresh_from_db(); self.assertEqual(self.trip.status, 'cancelled')
        self.assertTrue(response.data['data']['review_required'])
        self.created.assert_not_called()

    def test_timeout_does_not_create_second_refund_on_retry(self):
        self.created.side_effect = TimeoutError('synthetic timeout')
        first, second = self.cancel(), self.cancel()
        self.assertEqual(first.status_code, 200); self.assertEqual(second.status_code, 200)
        self.assertEqual(self.op().status, 'reconcile')
        self.created.assert_called_once()
        self.assertEqual(CompanyRefundLedger.objects.count(), 0)

    def test_pending_then_signed_success_posts_once(self):
        self.create_status = 'pending'; response = self.cancel()
        self.assertFalse(response.data['data']['refund_processed'])
        self.assertEqual(CompanyRefundLedger.objects.count(), 0)
        self.rows[0]['status'] = 'succeeded'
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.assertEqual(CompanyRefundLedger.objects.count(), 1)
        self.assertEqual(RefundPosting.objects.count(), 1)
        self.created.assert_called_once()

    def test_failed_result_never_posts_accounting(self):
        self.create_status = 'failed'
        response = self.cancel()
        self.assertTrue(response.data['data']['review_required'])
        self.assertFalse(response.data['data']['refund_processed'])
        self.assertEqual(RefundPosting.objects.count(), 0)

    def test_ledger_failure_reconciliation_repairs_without_new_money(self):
        from apps.earnings.services.refund_rules import RefundRulesService
        original = RefundRulesService.process_refund
        def fail_after_create(**kwargs):
            original(**kwargs)
            raise RuntimeError('synthetic crash after posting before marker')
        with patch.object(RefundRulesService, 'process_refund', side_effect=fail_after_create):
            self.cancel()
        self.assertEqual(self.op().status, 'succeeded')
        self.assertEqual(CompanyRefundLedger.objects.count(), 0)
        self.assertEqual(RefundPosting.objects.count(), 0)
        provider.reconcile_reserved_refund(self.op().pk)
        self.assertEqual(CompanyRefundLedger.objects.count(), 1)
        self.created.assert_called_once()

    def test_known_conflicting_ledger_is_held_not_duplicated(self):
        CompanyRefundLedger.objects.create(trip=self.trip, refund_amount=Decimal('-1.00'),
                                          stripe_refund_id='re_synthetic')
        self.cancel()
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.refund_status, 'processed_ledger_error')
        self.assertEqual(CompanyRefundLedger.objects.count(), 1)
        self.assertEqual(RefundPosting.objects.count(), 0)

    def test_late_terminal_conflict_preserves_posting_and_requires_review(self):
        self.cancel(); self.rows[0]['status'] = 'failed'
        provider.reconcile_reserved_refund(self.op().pk)
        self.assertEqual(self.op().status, 'reconcile')
        self.assertEqual(CompanyRefundLedger.objects.count(), 1)
        self.assertTrue(public_outcome(self.case().pk)['review_required'])
        self.created.assert_called_once()

    def test_reconciliation_endpoint_never_accepts_provider_facts(self):
        self.cancel(); self.pi.reset_mock()
        result = self.call(CancellationReconcileView, user=self.staff, receipt_id=self.case().pk,
                          payload={'status': 'succeeded'})
        self.assertEqual(result.status_code, 409); self.pi.assert_not_called()

    def test_unknown_old_terms_cancel_but_are_not_assigned_new_schedule(self):
        self.terms.delete()
        result = self.cancel()
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data['data']['review_required'])
        self.assertIsNone(result.data['data']['standard_refund_percent'])
        self.created.assert_not_called()
        self.assertEqual(BookingTermsAcceptance.objects.count(), 0)

    def test_disabled_legacy_route_preserved_but_bound_terms_cannot_fall_back(self):
        with override_settings(ACT_CANCELLATION_FLOW_ENABLED=False), patch.object(
                LegacyCancelView, 'handle_post', return_value=Response({'legacy': True})) as legacy:
            self.cancel()
            legacy.assert_not_called()
        self.created.assert_called_once()

    def test_disabled_unversioned_trip_delegates_legacy(self):
        self.terms.delete()
        with override_settings(ACT_CANCELLATION_FLOW_ENABLED=False), patch.object(
                LegacyCancelView, 'handle_post', return_value=Response({'legacy': True})) as legacy:
            self.assertTrue(self.cancel().data['legacy'])
            legacy.assert_called_once()
        self.created.assert_not_called()

    def test_missing_marked_evidence_never_reaches_legacy(self):
        self.terms.delete()
        self.trip.booking_details = {'_act_booking_terms': {'schema': 1, 'required': True}}
        self.trip.save(update_fields=['booking_details'])
        with override_settings(ACT_CANCELLATION_FLOW_ENABLED=False), patch.object(LegacyCancelView, 'handle_post') as legacy:
            self.assertEqual(self.cancel().status_code, 200)
            legacy.assert_not_called()
        self.created.assert_not_called()

    def test_started_completed_journeys_never_cancel_or_refund(self):
        for state in ('active', 'completed', 'expired', 'cancelled'):
            Trip.objects.filter(pk=self.trip.pk).update(status=state)
            self.assertEqual(self.cancel().status_code, 409)
        self.created.assert_not_called()
        self.assertEqual(CancellationCase.objects.count(), 0)

    def test_driver_en_route_is_stopped_without_marking_passenger_no_show(self):
        self.trip.status = 'driver_on_the_way'; self.trip.save(update_fields=['status'])
        self.assertEqual(self.cancel().status_code, 200)
        self.assertEqual(self.case().original_status, 'driver_on_the_way')
        self.created.assert_called_once()

    def test_database_guard_blocks_stale_save_and_bulk_updates(self):
        stale = Trip.objects.get(pk=self.trip.pk)
        self.cancel()
        stale.status = 'active'
        with self.assertRaises(IntegrityError), transaction.atomic(): stale.save(update_fields=['status'])
        for changed in ({'status': 'accepted'}, {'cost': '99.00'}, {'trip_time': '23:59:00'},
                        {'stripe_payment_intent': 'pi_forged'}, {'is_paid': False}, {'is_guest_driver': True}):
            with self.subTest(changed=changed), self.assertRaises(IntegrityError), transaction.atomic():
                Trip.objects.filter(pk=self.trip.pk).update(**changed)
        self.trip.refresh_from_db(); self.assertEqual(self.trip.status, 'cancelled')

    def test_database_guard_does_not_block_refund_metadata(self):
        self.cancel()
        Trip.objects.filter(pk=self.trip.pk).update(refund_error='synthetic support note')
        self.assertEqual(Trip.objects.get(pk=self.trip.pk).refund_error, 'synthetic support note')

    def test_review_cannot_change_existing_positive_reservation(self):
        self.near(20); self.cancel(); self.review(loss=5000)
        self.assertEqual(self.review(loss=1).status_code, 409)
        self.assertEqual(self.op().amount_pence, 5001)
        self.created.assert_called_once()

    def test_concurrent_cancellations_have_one_stop_refund_and_posting(self):
        barrier = Barrier(2)
        def run():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.cancel().status_code
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(results, [200, 200])
        self.assertEqual((CancellationCase.objects.count(), RefundReservation.objects.count(), RefundPosting.objects.count()), (1, 1, 1))
        self.created.assert_called_once()

    def test_start_cancellation_race_never_has_active_trip_and_refund(self):
        barrier = Barrier(2)
        def start():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    Trip.objects.filter(pk=self.trip.pk).update(status='active')
                    return 'started'
                except IntegrityError:
                    return 'blocked'
            finally: close_old_connections()
        def cancel():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.cancel().status_code
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(start), pool.submit(cancel)
            started, code = a.result(timeout=15), b.result(timeout=15)
        self.trip.refresh_from_db()
        if started == 'started':
            self.assertEqual(self.trip.status, 'active'); self.assertEqual(code, 409)
            self.created.assert_not_called()
        else:
            self.assertEqual(self.trip.status, 'cancelled'); self.assertEqual(code, 200)
            self.created.assert_called_once()

    def test_concurrent_reconciled_posting_is_exactly_once(self):
        self.create_status = 'pending'; self.cancel()
        self.operation = self.op()
        record_provider_refund(self.operation.pk, provider_result=self.refund(status='succeeded'))
        barrier = Barrier(2)
        def post():
            close_old_connections()
            try:
                barrier.wait(timeout=10); finalize_managed_refund(self.operation.pk)
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: post(), range(2)))
        self.assertEqual(CompanyRefundLedger.objects.count(), 1)
        self.assertEqual(RefundPosting.objects.count(), 1)
