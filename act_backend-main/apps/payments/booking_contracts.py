"""Internal database boundary; not called by live checkout/cancellation routes yet.

No Stripe/network/task calls. Settings select a *published* release (none by
 default); browser acknowledgements never select a policy. Provider observations
must come from authenticated provider reads/webhooks, never request.data. Pending,
failed and uncertain operations remain reserved until explicit reconciliation.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.payments.models import (
    PendingPayment, BookingTermsAcceptance, CancellationReceipt, RefundReservation,
)
from apps.trips.models import Trip
from apps.trips.services.cancellation_policy import (
    CANDIDATE_POLICY_VERSION, _pence, _utc, preview_cancellation_refund,
)


class ContractConflict(ValueError):
    """Fail closed; caller must present a safe review outcome, not refund denial."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def money_pence(value):
    number = Decimal(str(value)) * 100
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ContractConflict('Invalid exact GBP amount')
    return int(number)


def checked_snapshot(record):
    if digest(record.snapshot) != record.snapshot_sha256:
        raise ContractConflict('Stored terms checksum mismatch')
    return record.snapshot


def _pending_matches(pending, snapshot):
    return (digest(pending.trip_data) == snapshot['trip_data_sha256']
            and money_pence(pending.price_breakdown['total_cost']) == snapshot['quoted_pence']
            and pending.currency.upper() == snapshot['currency'])


@transaction.atomic(durable=True)
def capture_checkout_terms(pending_id, *, acknowledgement, locale,
                           received_at, confirmed_pickup_at):
    """Save before PaymentIntent creation. Missing config is a deliberate hold."""
    received = _utc(received_at, 'received_at')
    pickup = _utc(confirmed_pickup_at, 'confirmed_pickup_at')
    pending = PendingPayment.objects.select_for_update().get(pk=pending_id)
    old = BookingTermsAcceptance.objects.filter(pending_payment=pending).first()
    if old:
        s = checked_snapshot(old)
        expected = {'accepted': True, 'terms_version': s['terms_version'],
                    'terms_sha256': s['terms_sha256'], 'locale': s['locale']}
        if (not isinstance(acknowledgement, dict) or acknowledgement.get('accepted') is not True
                or acknowledgement != expected or locale != s['locale']
                or pickup.isoformat() != s['pickup_at'] or not _pending_matches(pending, s)):
            raise ContractConflict('Existing checkout acceptance differs')
        return old
    if pending.payment_intent_id:
        raise ContractConflict('Cannot invent acceptance after payment initiation')
    if pending.expires_at <= received:
        raise ContractConflict('Checkout has expired')
    release = getattr(settings, 'ACT_BOOKING_TERMS_RELEASE', None)
    if not isinstance(release, dict) or release.get('published') is not True:
        raise ContractConflict('No published terms release configured')
    if release.get('policy_version') != CANDIDATE_POLICY_VERSION:
        raise ContractConflict('Unsupported release policy')
    effective = _utc(datetime.fromisoformat(release['effective_at']), 'effective_at')
    if received < effective:
        raise ContractConflict('Terms release is not effective')
    doc = release.get('locales', {}).get(locale)
    if not isinstance(doc, dict) or not isinstance(doc.get('text'), str) or not doc['text'].strip():
        raise ContractConflict('No reviewed document for this locale')
    text_hash = hashlib.sha256(doc['text'].encode()).hexdigest()
    if text_hash != doc.get('sha256') or not re.fullmatch(r'[0-9a-f]{64}', doc.get('pdf_sha256', '')):
        raise ContractConflict('Published document hashes do not match')
    if not re.fullmatch(r'/documents/[A-Za-z0-9/_-]+\.pdf', doc.get('url', '')):
        raise ContractConflict('Invalid versioned document path')
    version = release.get('terms_version')
    if not isinstance(version, str) or not version.strip():
        raise ContractConflict('Missing terms version')
    expected = {'accepted': True, 'terms_version': version,
                'terms_sha256': text_hash, 'locale': locale}
    if (not isinstance(acknowledgement, dict) or acknowledgement.get('accepted') is not True
            or acknowledgement != expected):
        raise ContractConflict('Explicit matching terms acknowledgement required')
    local_pickup = pickup.astimezone(ZoneInfo('Europe/London'))
    stored_local = datetime.fromisoformat(
        f"{pending.trip_data['trip_date']}T{pending.trip_data['trip_time']}")
    if stored_local.tzinfo is not None or local_pickup.replace(tzinfo=None) != stored_local:
        raise ContractConflict('Confirmed pickup differs from priced checkout')
    amount = money_pence(pending.price_breakdown['total_cost'])
    if pending.currency.upper() != 'GBP' or amount <= 0 or pickup <= received:
        raise ContractConflict('Invalid currency, amount or pickup')
    snapshot = {
        'schema': 1, 'policy_version': release['policy_version'], 'terms_version': version,
        'terms_text': doc['text'], 'terms_sha256': text_hash, 'pdf_sha256': doc['pdf_sha256'],
        'document_url': doc['url'], 'locale': locale, 'effective_at': effective.isoformat(),
        'accepted_at': received.isoformat(), 'pickup_at': pickup.isoformat(),
        'quoted_pence': amount, 'currency': 'GBP', 'pending_reference': str(pending.pk),
        'trip_data_sha256': digest(pending.trip_data),
    }
    return BookingTermsAcceptance.objects.create(
        pending_payment=pending, snapshot=snapshot, snapshot_sha256=digest(snapshot))


@transaction.atomic
def bind_paid_terms(pending_id, trip_id, *, payment_intent_id, captured_pence):
    """Call in the existing fulfillment transaction, BEFORE deleting PendingPayment."""
    _pence(captured_pence, 'captured_pence')
    pending = PendingPayment.objects.select_for_update().get(pk=pending_id)
    trip = Trip.objects.select_for_update().get(pk=trip_id)
    record = BookingTermsAcceptance.objects.select_for_update().filter(pending_payment=pending).first()
    if record is None:
        return None  # Legacy/unknown stays legacy/unknown; never infer accepted terms.
    s = checked_snapshot(record)
    pickup = datetime.fromisoformat(s['pickup_at']).astimezone(ZoneInfo('Europe/London'))
    if (not _pending_matches(pending, s) or captured_pence != s['quoted_pence']
            or pending.payment_intent_id != payment_intent_id
            or trip.stripe_payment_intent != payment_intent_id or not trip.is_paid
            or money_pence(trip.cost) != captured_pence
            or trip.trip_date != pickup.date() or trip.trip_time != pickup.time().replace(tzinfo=None)
            or trip.passenger_id != pending.passenger_id):
        raise ContractConflict('Paid booking does not match accepted checkout')
    if record.trip_id is not None:
        if (record.trip_id, record.payment_intent_id, record.captured_pence) != (
                trip_id, payment_intent_id, captured_pence):
            raise ContractConflict('Acceptance already belongs to another payment or trip')
        return record
    record.trip = trip
    record.payment_intent_id = payment_intent_id
    record.captured_pence = captured_pence
    record.save(update_fields=['trip', 'payment_intent_id', 'captured_pence'])
    return record


@transaction.atomic
def record_cancellation_receipt(trip_id, *, received_at, kind='passenger_cancellation'):
    """Only records notification; NOT a public endpoint or a trip-state transition."""
    received = _utc(received_at, 'received_at')
    if kind not in ('passenger_cancellation', 'act_unable_to_supply', 'no_show', 'other'):
        raise ContractConflict('Unsupported cancellation kind')
    trip = Trip.objects.select_for_update().get(pk=trip_id)
    receipt = CancellationReceipt.objects.filter(trip=trip).first()
    if receipt:
        if receipt.kind != kind or received < receipt.received_at:
            raise ContractConflict('Earlier receipt/reason conflict requires review')
        return receipt
    return CancellationReceipt.objects.create(trip=trip, received_at=received, kind=kind)


@dataclass(frozen=True)
class PaymentObservation:
    """Trusted/reconciled provider facts. Never construct from passenger input."""
    payment_intent_id: str
    captured_pence: int
    refunded_pence: int
    pending_pence: int
    observed_at: datetime
    currency: str = 'GBP'
    settled: bool = True
    disputed: bool = False


def _check_observation(trip, evidence, assessed_at):
    for name in ('captured_pence', 'refunded_pence', 'pending_pence'):
        _pence(getattr(evidence, name), name)
    age = _utc(assessed_at, 'assessed_at') - _utc(evidence.observed_at, 'observed_at')
    if (not timedelta(0) <= age <= timedelta(minutes=5)
            or evidence.currency != 'GBP' or evidence.settled is not True
            or evidence.disputed is not False or evidence.pending_pence
            or evidence.refunded_pence > evidence.captured_pence
            or not trip.is_paid or not evidence.payment_intent_id.startswith('pi_')
            or evidence.payment_intent_id != trip.stripe_payment_intent):
        raise ContractConflict('Payment must be freshly reconciled before reservation/dispatch')


@transaction.atomic
def prepare_refund_reservation(receipt_id, *, evidence, assessed_at,
                               reviewed_loss_pence=None, review_reference=None, reviewer_id=None):
    """Assess using stored terms; reserve only. Returns (preview, operation or None)."""
    receipt = CancellationReceipt.objects.select_related('trip').get(pk=receipt_id)
    trip = Trip.objects.select_for_update().get(pk=receipt.trip_id)
    old = RefundReservation.objects.filter(receipt=receipt).first()
    if old:
        return old.assessment, old  # Re-reading never dispatches or changes its parameters.
    _check_observation(trip, evidence, assessed_at)
    record = BookingTermsAcceptance.objects.filter(trip=trip).first()
    if record is None:
        return {'outcome': 'accepted_terms_review_required', 'review_required': True}, None
    s = checked_snapshot(record)
    if (record.payment_intent_id != evidence.payment_intent_id
            or record.captured_pence != evidence.captured_pence):
        raise ContractConflict('Provider capture differs from bound acceptance')
    pickup = datetime.fromisoformat(s['pickup_at'])
    local_pickup = pickup.astimezone(ZoneInfo('Europe/London'))
    if (trip.trip_date != local_pickup.date()
            or trip.trip_time != local_pickup.time().replace(tzinfo=None)):
        raise ContractConflict('Amended journey requires reviewed pickup evidence')
    if reviewed_loss_pence is not None:
        reviewer = get_user_model().objects.get(pk=reviewer_id)
        if not reviewer.is_active or not reviewer.is_staff:
            raise ContractConflict('Active staff loss review required')
    elif reviewer_id is not None or review_reference is not None:
        raise ContractConflict('Incomplete loss review')
    result = asdict(preview_cancellation_refund(
        accepted_policy_version=s['policy_version'], confirmed_pickup_at=pickup,
        cancellation_received_at=receipt.received_at,
        captured_amount_pence=evidence.captured_pence, already_refunded_pence=evidence.refunded_pence,
        currency=evidence.currency, cancellation_kind=receipt.kind, journey_status=trip.status,
        reviewed_net_loss_pence=reviewed_loss_pence, loss_review_reference=review_reference))
    if result['review_required'] or not result['additional_refund_pence']:
        return result, None
    result.update({'reviewer_id': str(reviewer_id) if reviewer_id else None,
                   'review_reference': review_reference, 'reviewed_loss_pence': reviewed_loss_pence,
                   'assessed_at': _utc(assessed_at, 'assessed_at').isoformat(),
                   'already_refunded_pence': evidence.refunded_pence,
                   'accepted_terms_record': str(record.pk)})
    operation = RefundReservation.objects.create(
        receipt=receipt, payment_intent_id=evidence.payment_intent_id,
        amount_pence=result['additional_refund_pence'], assessment=result)
    return result, operation


@transaction.atomic(durable=True)
def claim_refund_dispatch(operation_id, *, evidence, claimed_at):
    """One claim before any future provider call. No automatic retry after uncertainty."""
    operation = RefundReservation.objects.select_related('receipt').get(pk=operation_id)
    trip = Trip.objects.select_for_update().get(pk=operation.receipt.trip_id)
    operation = RefundReservation.objects.select_for_update().get(pk=operation_id)
    if operation.status != 'prepared':
        return None
    _check_observation(trip, evidence, claimed_at)
    if (evidence.payment_intent_id != operation.payment_intent_id
            or evidence.refunded_pence != operation.assessment['already_refunded_pence']
            or operation.amount_pence > evidence.captured_pence - evidence.refunded_pence):
        raise ContractConflict('Refund balance changed; reconcile the reservation')
    record = BookingTermsAcceptance.objects.get(trip=trip)
    s = checked_snapshot(record)
    pickup = datetime.fromisoformat(s['pickup_at']).astimezone(ZoneInfo('Europe/London'))
    if (trip.status not in ('pending', 'accepted') or trip.trip_date != pickup.date()
            or trip.trip_time != pickup.time().replace(tzinfo=None)):
        raise ContractConflict('Journey changed since assessment; review before dispatch')
    if record.captured_pence != evidence.captured_pence or record.payment_intent_id != evidence.payment_intent_id:
        raise ContractConflict('Bound payment changed')
    operation.status = 'in_flight'
    operation.first_attempt_at = _utc(claimed_at, 'claimed_at')
    operation.save(update_fields=['status', 'first_attempt_at', 'updated_at'])
    return {'payment_intent': operation.payment_intent_id, 'amount': operation.amount_pence,
            'idempotency_key': operation.idempotency_key,
            'metadata': {'act_refund_operation': str(operation.pk)}}


@transaction.atomic
def record_provider_refund(operation_id, *, provider_result):
    """Only validated provider responses/webhooks. Does not post financial ledgers."""
    operation = RefundReservation.objects.select_for_update().get(pk=operation_id)
    p = provider_result
    allowed = ('pending', 'requires_action', 'succeeded', 'failed', 'canceled')
    if (operation.status == 'prepared' or type(p.get('amount')) is not int
            or p['amount'] != operation.amount_pence or p.get('currency') != 'gbp'
            or p.get('payment_intent') != operation.payment_intent_id
            or p.get('status') not in allowed
            or not re.fullmatch(r're_[A-Za-z0-9]+', p.get('id', ''))
            or operation.provider_refund_id not in (None, p['id'])):
        raise ContractConflict('Provider refund does not match reserved operation')
    if operation.status in ('succeeded', 'failed', 'canceled'):
        if p['status'] in ('pending', 'requires_action') or p['status'] == operation.status:
            return operation  # Duplicate/older notification must not regress final state.
        raise ContractConflict('Conflicting terminal provider result requires reconciliation')
    operation.provider_refund_id = p['id']
    operation.status = p['status']
    operation.save(update_fields=['provider_refund_id', 'status', 'updated_at'])
    return operation
