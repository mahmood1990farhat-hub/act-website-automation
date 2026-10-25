"""Checkout/fulfillment wiring for the reviewed booking-contract service.

Disabled unless ACT_BOOKING_TERMS_CHECKOUT_ENABLED is literally True. This file
ships no published release or effective date, and never calculates or sends refunds.
The server controls the requirement marker; client booking_details cannot opt out.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.payments.models import BookingTermsAcceptance
from apps.payments.booking_contracts import (
    ContractConflict, bind_paid_terms, capture_checkout_terms, checked_snapshot,
)

TERMS_MARKER = '_act_booking_terms'
REQUIRED_MARKER = {'schema': 1, 'required': True}


def checkout_booking_details(details):
    """Return a copy with a server-selected requirement, never a client policy ID."""
    if not isinstance(details, dict):
        raise ValidationError({'booking_details': _('Booking details must be an object.')})
    enabled = getattr(settings, 'ACT_BOOKING_TERMS_CHECKOUT_ENABLED', False)
    if type(enabled) is not bool:
        raise ContractConflict('Invalid checkout terms activation setting')
    result = dict(details)
    result.pop(TERMS_MARKER, None)
    if enabled:
        result[TERMS_MARKER] = dict(REQUIRED_MARKER)
    return result


def _terms_required(details):
    if not isinstance(details, dict):
        raise ContractConflict('Invalid stored booking details')
    marker = details.get(TERMS_MARKER)
    if marker is None:
        return False
    if (not isinstance(marker, dict) or marker != REQUIRED_MARKER
            or marker.get('required') is not True or type(marker.get('schema')) is not int):
        raise ContractConflict('Invalid stored terms requirement')
    return True


def _confirmed_pickup(trip_data):
    """Resolve only unique UK wall times. Ambiguous/nonexistent times need review."""
    local = datetime.fromisoformat(f"{trip_data['trip_date']}T{trip_data['trip_time']}")
    if local.tzinfo is not None:
        raise ContractConflict('Expected priced UK local pickup time')
    london = ZoneInfo('Europe/London')
    instants = set()
    for fold in (0, 1):
        candidate = local.replace(tzinfo=london, fold=fold).astimezone(timezone.utc)
        if candidate.astimezone(london).replace(tzinfo=None) == local:
            instants.add(candidate)
    if len(instants) != 1:
        raise ContractConflict('Pickup clock-change ambiguity requires explicit resolution')
    return instants.pop()


def capture_before_payment(pending, *, acknowledgement, locale, received_at):
    """Called by both real initiation handlers, before PaymentIntent.create.

    Preserve an acceptance on provider failure; do not invent success or remove
    evidence. The existing durable service commits before returning this record.
    """
    if not _terms_required(pending.booking_details):
        return None
    try:
        return capture_checkout_terms(
            pending.pk, acknowledgement=acknowledgement, locale=locale,
            received_at=received_at, confirmed_pickup_at=_confirmed_pickup(pending.trip_data))
    except (ContractConflict, ValueError, KeyError, TypeError) as exc:
        raise ValidationError({'booking_terms': _(
            'Booking terms could not be confirmed. Refresh checkout and review the terms, '
            'or contact ACT before making payment.')}) from exc


def _settled_amount(payment_intent):
    amount = payment_intent.get('amount_received')
    if (payment_intent.get('status') != 'succeeded' or type(amount) is not int or amount <= 0
            or payment_intent.get('currency') != 'gbp'):
        raise ContractConflict('New-policy booking requires verified settled GBP payment')
    return amount


def bind_before_pending_delete(pending, trip, payment_intent):
    """Existing verified-webhook transaction must bind before deleting pending data.

    Current rollout settings do not override what THIS checkout required. Missing
    required acceptance is a retryable fulfillment error, never legacy fallback.
    """
    if not connection.in_atomic_block:
        raise ContractConflict('Terms binding requires the fulfillment transaction')
    required = _terms_required(pending.booking_details)
    record = BookingTermsAcceptance.objects.filter(pending_payment_id=pending.pk).first()
    if record is None:
        if required:
            raise ContractConflict('Required checkout acceptance is missing')
        return None
    return bind_paid_terms(
        pending.pk, trip.pk, payment_intent_id=payment_intent['id'],
        captured_pence=_settled_amount(payment_intent))


def verify_duplicate_terms(trip, payment_intent):
    """Duplicate verified success must not backfill or discard accepted terms."""
    required = _terms_required(trip.booking_details or {})
    record = BookingTermsAcceptance.objects.filter(trip_id=trip.pk).first()
    if record is None:
        if required:
            raise ContractConflict('Confirmed booking is missing required acceptance')
        return
    snapshot = checked_snapshot(record)
    amount = _settled_amount(payment_intent)
    if (record.payment_intent_id != payment_intent['id']
            or trip.stripe_payment_intent != payment_intent['id']
            or record.captured_pence != amount or snapshot['quoted_pence'] != amount):
        raise ContractConflict('Duplicate payment differs from bound acceptance')
