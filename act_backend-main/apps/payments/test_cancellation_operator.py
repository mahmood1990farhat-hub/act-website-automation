"""Read-only operator API tests; synthetic records, no payment or mail requests."""
from datetime import datetime, timedelta, timezone
import json
import socket
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.payments.booking_contracts import digest
from apps.payments.models import BookingTermsAcceptance, CancellationReceipt, CancellationCase, RefundReservation
from apps.payments.cancellation_views import CancellationReviewView, CancellationReconcileView
from apps.payments.cancellation_operator import CancellationQueueView, CancellationOperatorReviewView
from apps.trips.models import Trip
from apps.trips.services.cancellation_policy import CANDIDATE_POLICY_VERSION


@override_settings(ACT_REFUND_PROVIDER_ENABLED=True, ACT_REFUND_DISPATCH_ENABLED=True)
class CancellationOperatorTests(TestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.at = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        self.staff = get_user_model().objects.create(email='reviewer@example.invalid', is_active=True, is_staff=True)
        self.staff.user_permissions.add(Permission.objects.get(content_type__app_label='payments', codename='review_cancellationcase'))
        self.case, self.record = self.make_case(1)
        self.payment = self.enterContext(patch('stripe.PaymentIntent.retrieve', side_effect=AssertionError('GET must not read Stripe')))
        self.refund = self.enterContext(patch('stripe.Refund.create', side_effect=AssertionError('GET must not refund')))
        self.mail = self.enterContext(patch('django.core.mail.send_mail', side_effect=AssertionError('GET must not send mail')))
        original = socket.socket.connect
        def local_only(sock, address):
            if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
                raise AssertionError('No external network in operator tests')
            return original(sock, address)
        self.enterContext(patch('socket.socket.connect', local_only))

    def make_case(self, number, terms=True):
        pickup = self.at + timedelta(hours=20)
        trip = Trip.objects.create(pickup_lat=0, pickup_lng=0, dropoff_lat=1, dropoff_lng=1,
            trip_date=pickup.date(), trip_time=pickup.time().replace(tzinfo=None), passengers_count=1,
            cost='100.01', status='cancelled', cancelled_at=self.at, is_paid=True,
            stripe_payment_intent=f'pi_synthetic{number}', refund_status='manual_review',
            passenger_email='private-passenger@example.invalid', passenger_phone='private-phone')
        receipt = CancellationReceipt.objects.create(trip=trip, received_at=self.at, kind='passenger_cancellation')
        case = CancellationCase.objects.create(receipt=receipt, original_status='pending', pickup_at=pickup, stopped_at=self.at)
        record = None
        if terms:
            snapshot = {'policy_version': CANDIDATE_POLICY_VERSION, 'terms_version':'synthetic-v1',
                'terms_text':'Synthetic review terms only.', 'terms_sha256':'a'*64, 'locale':'en',
                'accepted_at':(self.at-timedelta(days=1)).isoformat(), 'pickup_at':pickup.isoformat(),
                'quoted_pence':10001, 'currency':'GBP'}
            record = BookingTermsAcceptance.objects.create(trip=trip, captured_pence=10001,
                payment_intent_id=trip.stripe_payment_intent, snapshot=snapshot, snapshot_sha256=digest(snapshot))
        return case, record

    def get(self, *, detail=False, user='staff', query='', receipt=None):
        request = APIRequestFactory().get('/synthetic/'+query)
        if user == 'staff': user = self.staff
        if user is not None: force_authenticate(request, user=user)
        if detail:
            return CancellationOperatorReviewView.as_view()(request, receipt_id=receipt or self.case.pk)
        return CancellationQueueView.as_view()(request)

    def test_permission_required_for_both_reads(self):
        outsider = get_user_model().objects.create(email='no-permission@example.invalid', is_staff=True)
        for detail in (False, True):
            for user in (None, outsider):
                self.assertIn(self.get(detail=detail, user=user).status_code, (401, 403))

    def test_inactive_or_nonstaff_user_cannot_read(self):
        for attribute in ('is_active', 'is_staff'):
            setattr(self.staff, attribute, False); self.staff.save(update_fields=[attribute])
            self.assertEqual(self.get(detail=True).status_code, 403)
            setattr(self.staff, attribute, True); self.staff.save(update_fields=[attribute])

    def test_list_contains_only_safe_summary_and_no_store(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pagination']['count'], 1)
        row = response.data['data'][0]
        self.assertEqual(row['cancellation_id'], str(self.case.pk))
        self.assertEqual(row['refund_status'], 'manual_review')
        self.assertEqual(set(row), {'cancellation_id','trip_id','booking_reference','journey_status',
            'cancellation_received_at','refund_status','has_hold'})
        self.assertIn('no-store', response['Cache-Control'])

    def test_pagination_and_exact_trip_filter(self):
        for i in range(2, 23): self.make_case(i, terms=False)
        a, b = self.get(), self.get(query='?page=2')
        self.assertEqual(len(a.data['data']), 20); self.assertEqual(len(b.data['data']), 2)
        self.assertTrue(a.data['pagination']['has_next']); self.assertFalse(b.data['pagination']['has_next'])
        self.assertFalse({r['cancellation_id'] for r in a.data['data']} & {r['cancellation_id'] for r in b.data['data']})
        filtered = self.get(query=f'?trip_id={self.case.receipt.trip_id}')
        self.assertEqual(filtered.data['pagination']['count'], 1)

    def test_invalid_filters_rejected(self):
        for query in ('?page=0','?page=-1','?page=1.5','?page=1000001','?trip_id=x','?trip_id=','?amount=500'):
            self.assertEqual(self.get(query=query).status_code, 400)

    def test_detail_displays_recorded_terms_not_current_release(self):
        with override_settings(ACT_BOOKING_TERMS_RELEASE={'terms_version':'not-accepted'}):
            response = self.get(detail=True)
        data = response.data['data']
        self.assertEqual(data['terms']['terms_version'], 'synthetic-v1')
        self.assertEqual(data['terms_evidence'], 'recorded')
        self.assertEqual(data['captured_pence'], 10001)
        self.assertTrue(data['actions']['review']); self.assertFalse(data['actions']['reconcile'])
        self.assertIn('no-store', response['Cache-Control'])

    def test_unknown_terms_never_receive_new_policy(self):
        case, _ = self.make_case(2, terms=False)
        data = self.get(detail=True, receipt=case.pk).data['data']
        self.assertEqual(data['terms_evidence'], 'unknown'); self.assertIsNone(data['terms'])
        self.assertFalse(data['actions']['review'])

    def test_invalid_snapshot_disables_review_without_exposing_raw_snapshot(self):
        self.record.snapshot['quoted_pence'] = 1; self.record.save(update_fields=['snapshot'])
        data = self.get(detail=True).data['data']
        self.assertEqual(data['terms_evidence'], 'inconsistent'); self.assertIsNone(data['terms'])
        self.assertFalse(data['actions']['review'])

    def test_disabled_flags_never_enable_writes_in_presentation(self):
        for change in ({'ACT_REFUND_PROVIDER_ENABLED':False}, {'ACT_REFUND_DISPATCH_ENABLED':False},
                       {'ACT_REFUND_DISPATCH_ENABLED':'True'}):
            with override_settings(**change):
                self.assertFalse(self.get(detail=True).data['data']['actions']['review'])

    def test_hold_and_final_zero_decision_are_not_new_refund_actions(self):
        self.case.hold_reason='synthetic_hold'; self.case.save(update_fields=['hold_reason'])
        self.assertFalse(self.get(detail=True).data['data']['actions']['review'])
        self.case.hold_reason=''; self.case.decision={'final':True,'additional_refund_pence':0}
        self.case.save(update_fields=['hold_reason','decision'])
        data=self.get(detail=True).data['data']
        self.assertEqual(data['refund_status'], 'not_due'); self.assertFalse(data['actions']['review'])

    def test_attempted_refund_can_be_reconciled_not_replaced(self):
        op=RefundReservation.objects.create(receipt=self.case.receipt, payment_intent_id=self.record.payment_intent_id,
            amount_pence=5001, assessment={}, status='pending', first_attempt_at=self.at)
        data=self.get(detail=True).data['data']
        self.assertFalse(data['actions']['review']); self.assertTrue(data['actions']['reconcile'])
        self.assertEqual(data['operation']['amount_pence'],5001)
        self.assertFalse(data['refund_processed']); self.assertFalse(data['operation']['accounting_posted'])
        op.first_attempt_at=None; op.status='prepared'; op.save()
        self.assertFalse(self.get(detail=True).data['data']['actions']['reconcile'])

    def test_reads_do_not_change_records_call_providers_or_reveal_contacts(self):
        before=list(CancellationCase.objects.values())
        responses=[self.get(), self.get(detail=True)]
        self.assertEqual(before,list(CancellationCase.objects.values()))
        self.payment.assert_not_called(); self.refund.assert_not_called(); self.mail.assert_not_called()
        output=json.dumps([response.data for response in responses])
        for secret in ('private-passenger@example.invalid','private-phone','pi_synthetic1'):
            self.assertNotIn(secret,output)

    def test_original_post_methods_and_routes_are_preserved(self):
        self.assertIs(CancellationOperatorReviewView.post, CancellationReviewView.post)
        from apps.payments.urls import urlpatterns
        self.assertIs(next(p for p in urlpatterns if str(p.pattern).endswith('/review/')).callback.view_class,
                      CancellationOperatorReviewView)
        self.assertIs(next(p for p in urlpatterns if str(p.pattern).endswith('/reconcile/')).callback.view_class,
                      CancellationReconcileView)

    def test_missing_case_is_404_not_an_empty_or_created_case(self):
        self.assertEqual(self.get(detail=True,receipt=uuid4()).status_code,404)
        self.assertEqual(CancellationCase.objects.count(),1)
