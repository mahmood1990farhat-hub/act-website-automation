"""Read-only operator presentation for the EXISTING cancellation review actions.

GET never calls Stripe, assesses a loss, sends mail or changes a case. Action
availability is advisory; inherited POST methods recheck staff permissions and
all financial/state guards. No customer contact/document data in this queue.
"""
from datetime import datetime
import re

from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.booking_contracts import checked_snapshot, ContractConflict, money_pence
from apps.payments.cancellation_flow import _staff, public_outcome, assessment_status
from apps.payments.cancellation_views import CancellationReviewView
from apps.payments.models import (
    BookingTermsAcceptance, CancellationCase, RefundReservation, RefundPosting,
)
from apps.trips.services.cancellation_policy import CANDIDATE_POLICY_VERSION, _utc


def _positive(value, field, maximum):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,17}', value):
        raise ValidationError({field: 'Use a positive whole number.'})
    number = int(value)
    if number > maximum:
        raise ValidationError({field: 'Value is outside the supported range.'})
    return number


def _summary(case):
    trip = case.receipt.trip
    try:
        operation = case.receipt.refund_reservation
    except RefundReservation.DoesNotExist:
        operation = None
    state = operation.status if operation else ('not_due' if case.decision.get('final') else 'manual_review')
    if case.hold_reason:
        state = 'manual_review'
    return {'cancellation_id': str(case.pk), 'trip_id': trip.pk,
            'booking_reference': f'ACT-{trip.pk:06d}', 'journey_status': trip.status,
            'cancellation_received_at': case.receipt.received_at.isoformat(),
            'refund_status': state, 'has_hold': bool(case.hold_reason)}


def operator_detail(case):
    """Allowlisted evidence only; no fresh provider observation is claimed."""
    trip = case.receipt.trip
    operation = RefundReservation.objects.filter(receipt_id=case.pk).first()
    record = BookingTermsAcceptance.objects.filter(trip=trip).first()
    terms, evidence = None, 'unknown'
    valid = False
    if record:
        try:
            s = checked_snapshot(record)
            pickup = _utc(datetime.fromisoformat(s['pickup_at']), 'pickup_at')
            _utc(datetime.fromisoformat(s['accepted_at']), 'accepted_at')
            if (not isinstance(s.get('terms_version'), str) or not isinstance(s.get('terms_text'), str)
                    or s.get('currency') != 'GBP' or type(record.captured_pence) is not int
                    or record.captured_pence <= 0 or record.captured_pence != s.get('quoted_pence')
                    or record.payment_intent_id != trip.stripe_payment_intent
                    or record.captured_pence != money_pence(trip.cost)
                    or case.pickup_at != pickup):
                raise ContractConflict('Bound terms evidence is inconsistent')
            terms = {name: s[name] for name in ('terms_version', 'policy_version', 'locale',
                     'terms_sha256', 'accepted_at', 'pickup_at', 'terms_text')}
            evidence = 'recorded'
            valid = s['policy_version'] == CANDIDATE_POLICY_VERSION
            if not valid:
                evidence = 'unsupported_version'
        except (ValueError, KeyError, TypeError, AttributeError):
            evidence = 'inconsistent'
    stopped = False
    try:
        assessment_status(trip, case.receipt)
        stopped = trip.status == 'cancelled'
    except ContractConflict:
        pass
    provider = getattr(settings, 'ACT_REFUND_PROVIDER_ENABLED', False) is True
    dispatch = getattr(settings, 'ACT_REFUND_DISPATCH_ENABLED', False) is True
    final = case.decision.get('final') is True
    review_allowed = bool(valid and stopped and not case.hold_reason and trip.is_paid
                          and not final and operation is None and provider and dispatch)
    reconcile_allowed = bool(provider and operation and operation.first_attempt_at is not None)
    if case.hold_reason or not stopped:
        reason = 'This case has a journey/evidence hold. Use the support review process.'
    elif not valid:
        reason = 'Accepted terms are unknown or inconsistent. Do not apply the new policy retrospectively.'
    elif operation or final:
        reason = 'An assessment or refund operation already exists. This screen cannot replace it or send another refund.'
    elif not provider or not dispatch:
        reason = 'Refund actions are paused by server configuration. Viewing this case does not enable them.'
    else:
        reason = 'Record evidenced net loss, then explicitly confirm. The backend determines any refund.'
    return {**public_outcome(case.pk), 'operator_schema': 1,
        'booking_reference': f'ACT-{trip.pk:06d}', 'hold_reason': case.hold_reason,
        'assessment': case.decision, 'terms_evidence': evidence, 'terms': terms,
        'captured_pence': record.captured_pence if evidence == 'recorded' else None,
        'currency': 'GBP', 'stopped_at': case.stopped_at.isoformat(),
        'original_status': case.original_status,
        'operation': None if operation is None else {
            'status': operation.status, 'amount_pence': operation.amount_pence,
            'first_attempt_at': operation.first_attempt_at.isoformat() if operation.first_attempt_at else None,
            'updated_at': operation.updated_at.isoformat(),
            'accounting_posted': RefundPosting.objects.filter(reservation=operation).exists(),
        },
        'accounting_status': trip.refund_status,
        'actions': {'review': review_allowed, 'reconcile': reconcile_allowed, 'reason': reason},
        'read_at': timezone.now().isoformat()}


@method_decorator(never_cache, name='dispatch')
class CancellationQueueView(APIView):
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'head', 'options']

    def get(self, request):
        _staff(request.user)
        if set(request.query_params) - {'page', 'trip_id'}:
            raise ValidationError('Only page and trip_id filters are supported.')
        page = _positive(request.query_params.get('page', '1'), 'page', 1000000)
        qs = CancellationCase.objects.select_related('receipt__trip', 'receipt__refund_reservation')
        if 'trip_id' in request.query_params:
            qs = qs.filter(receipt__trip_id=_positive(request.query_params['trip_id'], 'trip_id', 9007199254740991))
        qs = qs.order_by('-receipt__received_at', '-receipt_id')
        size, count = 20, qs.count()
        rows = qs[(page - 1) * size:page * size]
        return Response({'success': True, 'data': [_summary(case) for case in rows],
                         'pagination': {'page': page, 'page_size': size, 'count': count,
                                        'has_next': page * size < count}})


@method_decorator(never_cache, name='dispatch')
class CancellationOperatorReviewView(CancellationReviewView):
    """Reuse the exact existing POST; extend only its read-only representation."""
    def get(self, request, receipt_id):
        _staff(request.user)
        try:
            case = CancellationCase.objects.select_related('receipt__trip').get(pk=receipt_id)
        except CancellationCase.DoesNotExist:
            raise NotFound('Cancellation case not found.') from None
        return Response({'success': True, 'data': operator_detail(case)})
