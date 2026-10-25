"""Managed pre-journey cancellation. No provider call inside a DB transaction.

The route owns authentication, server receipt time and choice of passenger intent.
The durable stop survives Stripe outages. Legacy terms require review, never the
new percentages. Service writes are serialized Trip -> case -> reservation.
"""
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, NotFound

from apps.trips.models import Trip
from apps.payments.models import (
    BookingTermsAcceptance, CancellationReceipt, RefundReservation,
    CancellationCase, RefundPosting,
)
from apps.payments.booking_contracts import (
    ContractConflict, checked_snapshot, record_cancellation_receipt,
    prepare_refund_reservation, _check_observation,
)
from apps.trips.services.cancellation_policy import _utc

STOPPABLE = ('pending', 'accepted', 'driver_on_the_way')


def passenger_filter(user):
    """A matching email never grants access to another registered passenger's trip."""
    q = Q(passenger_id=user.passenger_profile.pk)
    if user.email:
        q |= Q(passenger__isnull=True, passenger_email__iexact=user.email)
    return q


def managed_booking(trip):
    details = trip.booking_details if isinstance(trip.booking_details, dict) else {}
    return (getattr(settings, 'ACT_CANCELLATION_FLOW_ENABLED', False) is True
            or CancellationReceipt.objects.filter(trip=trip).exists()
            or BookingTermsAcceptance.objects.filter(trip=trip).exists()
            or '_act_booking_terms' in details)


def _staff(actor):
    user = get_user_model().objects.get(pk=actor.pk)
    if not (user.is_active and user.is_staff and user.has_perm('payments.review_cancellationcase')):
        raise PermissionDenied('Cancellation review permission required.')
    return user


def assessment_status(trip, receipt):
    """Project a durably stopped case to its verified pre-journey calculator state.

    Old internal calculation-only fixtures/operations without a managed case retain
    their original status contract. Actual routed cancellations always have a case.
    """
    case = CancellationCase.objects.filter(receipt=receipt).first()
    if case is None:
        return trip.status
    if (trip.status != 'cancelled' or trip.cancelled_at != case.stopped_at
            or case.original_status not in STOPPABLE or case.hold_reason):
        raise ContractConflict('Managed cancellation requires a verified stopped journey')
    # A driver en route is not a started passenger journey.
    return 'accepted' if case.original_status == 'driver_on_the_way' else case.original_status


@transaction.atomic(durable=True)
def stop_passenger_journey(trip_id, *, actor, received_at):
    """Authorise again under the trip lock and commit before any money operation."""
    user = get_user_model().objects.get(pk=actor.pk)
    if not (user.is_active and user.account_type == 'passenger'
            and user.is_profile_completed and user.is_admin_verified
            and hasattr(user, 'passenger_profile')):
        raise PermissionDenied('An eligible passenger account is required.')
    received = _utc(received_at, 'received_at')
    try:
        trip = Trip.objects.select_for_update().get(passenger_filter(user), pk=trip_id)
    except Trip.DoesNotExist:
        raise NotFound('Journey not found.') from None
    case = CancellationCase.objects.filter(receipt__trip=trip).select_related('receipt').first()
    if case:
        if received < case.receipt.received_at:
            case.hold_reason = 'earlier_receipt_requires_review'
            case.save(update_fields=['hold_reason'])
        return case, False
    if trip.status not in STOPPABLE:
        raise ContractConflict('This journey requires ACT support; it was not cancelled by this request')
    if CancellationReceipt.objects.filter(trip=trip).exists():
        raise ContractConflict('Existing cancellation evidence requires ACT support')
    receipt = record_cancellation_receipt(trip.pk, received_at=received)
    pickup, hold = None, ''
    record = BookingTermsAcceptance.objects.filter(trip=trip).first()
    if record:
        try:
            snapshot = checked_snapshot(record)
            pickup = _utc(datetime.fromisoformat(snapshot['pickup_at']), 'pickup_at')
        except (ValueError, KeyError, TypeError):
            hold = 'accepted_terms_evidence_requires_review'
    stopped = timezone.now()
    case = CancellationCase.objects.create(
        receipt=receipt, original_status=trip.status, pickup_at=pickup,
        stopped_at=stopped, requested_by=user, hold_reason=hold)
    trip.status = 'cancelled'
    trip.cancelled_at = stopped
    trip.refund_status = 'manual_review' if trip.is_paid else 'not_applicable'
    trip.refund_error = ''
    trip.save(update_fields=['status', 'cancelled_at', 'refund_status', 'refund_error'])
    return case, True


@transaction.atomic
def assess_stopped_case(receipt_id, *, evidence, assessed_at, actor=None,
                        reviewed_loss_pence=None, review_reference=None):
    case = CancellationCase.objects.select_related('receipt').get(pk=receipt_id)
    trip = Trip.objects.select_for_update().get(pk=case.receipt.trip_id)
    case = CancellationCase.objects.select_for_update().get(pk=receipt_id)
    assessment_status(trip, case.receipt)
    reviewer = _staff(actor) if actor is not None else None
    if reviewed_loss_pence is not None and reviewer is None:
        raise PermissionDenied('A staff review is required for a cancellation deduction.')
    if reviewer is not None:
        if (type(reviewed_loss_pence) is not int or reviewed_loss_pence < 0
                or not isinstance(review_reference, str) or not 8 <= len(review_reference.strip()) <= 200):
            raise ContractConflict('Provide an evidenced net loss in pence and a review reference')
    requested = {'reviewer_id': str(reviewer.pk) if reviewer else None,
                 'reviewed_loss_pence': reviewed_loss_pence,
                 'review_reference': review_reference.strip() if reviewer else None}
    if case.decision and case.decision.get('final'):
        if reviewer and case.decision.get('review') != requested:
            raise ContractConflict('A final assessment already exists; adjustments need separate review')
        return RefundReservation.objects.filter(receipt_id=receipt_id).first()
    if not trip.is_paid:
        case.decision = {'final': True, 'outcome': 'unpaid_no_refund_due',
                         'review_required': False, 'additional_refund_pence': 0}
        case.save(update_fields=['decision'])
        return None
    _check_observation(trip, evidence, assessed_at)
    result, operation = prepare_refund_reservation(
        receipt_id, evidence=evidence, assessed_at=assessed_at,
        reviewed_loss_pence=reviewed_loss_pence,
        review_reference=requested['review_reference'],
        reviewer_id=reviewer.pk if reviewer else None)
    case.decision = {**result, 'final': not result['review_required'], 'review': requested}
    case.save(update_fields=['decision'])
    if result['review_required']:
        trip.refund_status = 'manual_review'
    elif operation:
        trip.refund_status = operation.status
    else:
        trip.refund_status = 'not_due'
    trip.save(update_fields=['refund_status'])
    return operation


def process_stopped_case(receipt_id, *, actor=None, reviewed_loss_pence=None, review_reference=None):
    """One assessment/dispatch. Failures leave the committed cancellation intact."""
    from apps.payments.refund_provider import observe_payment, dispatch_reserved_refund
    if actor is not None:
        _staff(actor)  # Deny/validate before even a provider READ.
        if (type(reviewed_loss_pence) is not int or reviewed_loss_pence < 0
                or not isinstance(review_reference, str) or not 8 <= len(review_reference.strip()) <= 200):
            raise ContractConflict('Provide reviewed net loss and its evidence reference')
    case = CancellationCase.objects.select_related('receipt__trip').get(pk=receipt_id)
    trip = case.receipt.trip
    if case.hold_reason:
        return case
    # No new policy is inferred for an unversioned booking.
    record = BookingTermsAcceptance.objects.filter(trip=trip).first()
    if trip.is_paid and record is None:
        if actor is not None:
            raise ContractConflict('Historic accepted terms need separate support review')
        return case
    if not trip.is_paid and record and record.captured_pence:
        raise ContractConflict('Payment flag conflicts with captured acceptance evidence')
    operation = RefundReservation.objects.filter(receipt_id=receipt_id).first()
    if operation:
        if actor and (str(actor.pk) != case.decision.get('review', {}).get('reviewer_id')
                      or reviewed_loss_pence != case.decision.get('review', {}).get('reviewed_loss_pence')
                      or (review_reference or '').strip() != case.decision.get('review', {}).get('review_reference')):
            raise ContractConflict('An assessment already exists; do not silently change its amount')
    else:
        evidence = observe_payment(trip.stripe_payment_intent) if trip.is_paid else None
        operation = assess_stopped_case(receipt_id, evidence=evidence, assessed_at=timezone.now(),
                                         actor=actor, reviewed_loss_pence=reviewed_loss_pence,
                                         review_reference=review_reference)
    if operation and operation.status == 'prepared':
        dispatch_reserved_refund(operation.pk)
    case.refresh_from_db()
    return case


@transaction.atomic
def finalize_managed_refund(operation_id):
    """Mirror authenticated provider state and post pre-journey accounting once.

    No posting for pending/failed/unknown results. Existing earnings/ambiguous
    ledger history require an accounting review; never debit a driver speculatively.
    """
    operation = RefundReservation.objects.select_related('receipt').get(pk=operation_id)
    if not CancellationCase.objects.filter(pk=operation.receipt_id).exists():
        return  # Unconnected prior service fixtures are not production cancellations.
    trip = Trip.objects.select_for_update().get(pk=operation.receipt.trip_id)
    operation = RefundReservation.objects.select_for_update().get(pk=operation_id)
    if trip.status != 'cancelled':
        raise ContractConflict('Do not post a refund for a journey that is not stopped')
    trip.stripe_refund_id = operation.provider_refund_id
    trip.refund_status = {'succeeded': 'processed', 'reconcile': 'manual_review',
                          'requires_action': 'manual_review', 'canceled': 'manual_review'}.get(
                              operation.status, operation.status)
    trip.refund_error = ''
    if operation.status == 'succeeded':
        total = operation.assessment['already_refunded_pence'] + operation.amount_pence
        trip.refund_amount = Decimal(total) / Decimal(100)
        from apps.earnings.models import DriverEarningLedger, DriverRefundLedger, CompanyRefundLedger
        from apps.earnings.services.refund_rules import RefundRulesService
        if not RefundPosting.objects.filter(reservation=operation).exists():
            existing = list(CompanyRefundLedger.objects.filter(stripe_refund_id=operation.provider_refund_id))
            amount = Decimal(operation.amount_pence) / Decimal(100)
            blocked = (DriverEarningLedger.objects.filter(trip=trip).exists()
                       or DriverRefundLedger.objects.filter(stripe_refund_id=operation.provider_refund_id).exists()
                       or len(existing) > 1)
            if existing and not blocked:
                entry = existing[0]
                blocked = entry.trip_id != trip.pk or entry.refund_amount != -amount or entry.currency != 'GBP'
            if blocked:
                trip.refund_status = 'processed_ledger_error'
                trip.refund_error = 'Existing earnings or ledger history requires accounting review.'
            else:
                # If any create or marker write fails, this entire transaction rolls
                # back. A later provider reconciliation retries posting, not payment.
                if not existing:
                    _, entry = RefundRulesService.process_refund(
                        trip=trip, refund_amount=amount, stripe_refund_id=operation.provider_refund_id)
                RefundPosting.objects.create(reservation=operation, company_refund=entry)
    trip.save(update_fields=['refund_status', 'refund_amount', 'refund_error', 'stripe_refund_id'])


def public_outcome(receipt_id):
    case = CancellationCase.objects.select_related('receipt__trip').get(pk=receipt_id)
    trip = case.receipt.trip
    op = RefundReservation.objects.filter(receipt_id=receipt_id).first()
    state = op.status if op else ('not_due' if case.decision.get('final') else 'manual_review')
    if case.hold_reason:
        state = 'manual_review'
    return {'trip_id': trip.pk, 'status': trip.status, 'cancellation_id': str(case.pk),
            'cancellation_received_at': case.receipt.received_at.isoformat(),
            'refund_status': state, 'refund_processed': state == 'succeeded',
            'refund_amount': str(Decimal(op.amount_pence) / 100) if op and state == 'succeeded' else None,
            'review_required': state in ('manual_review', 'reconcile', 'requires_action', 'failed', 'canceled'),
            'standard_refund_percent': case.decision.get('standard_refund_percent')}
