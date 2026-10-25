"""Reconnect managed cancellations to EXISTING email/PDF functions, not new designs.

Only the request that creates the durable cancellation case calls this helper.
Existing asynchronous send functions report neither SMTP acceptance nor inbox
receipt; 'requested' below means invocation only. No automatic resend/retry is
introduced. This is not a durable email outbox or an exactly-once delivery claim.
"""
import logging

from django.db import connection, transaction

from apps.payments.booking_contracts import ContractConflict
from apps.payments.models import CancellationCase
from apps.trips.models import Trip
from apps.trips.services.booking_confirmation import ensure_cancellation_confirmation_pdf
from utils.common.email import (
    send_passenger_trip_cancellation_to_passenger,
    send_passenger_trip_cancellation_to_admin,
)

logger = logging.getLogger(__name__)


def request_existing_cancellation_assets(case_id):
    """Use the original templates, language selection, assets and download links.

    The existing neutral refund wording refers to terms accepted when booking;
    it does not assume that cancellation equals a completed/full refund. Do not
    inject new English-only policy text into the multilingual message renderer.
    """
    if connection.in_atomic_block:
        raise ContractConflict('Cancellation must commit before document/email follow-up')
    case = CancellationCase.objects.select_related('receipt', 'requested_by').get(pk=case_id)
    trip = Trip.objects.get(pk=case.receipt.trip_id)
    if trip.status != 'cancelled' or trip.cancelled_at != case.stopped_at:
        raise ContractConflict('Cancellation confirmation requires a committed stopped case')
    result = {'pdf': 'review_required', 'passenger_email': 'not_requested',
              'admin_email': 'not_requested'}
    try:
        # The preserved generator uses FileField.save(save=True), which saves the
        # whole Trip. Read under its row lock to avoid overwriting a concurrent
        # refund/accounting update with a stale in-memory Trip snapshot.
        with transaction.atomic():
            trip = Trip.objects.select_for_update().get(pk=case.receipt.trip_id)
            if trip.status != 'cancelled' or trip.cancelled_at != case.stopped_at:
                raise ContractConflict('Journey state changed before document preparation')
            ensure_cancellation_confirmation_pdf(trip)
            trip.refresh_from_db()
            if not trip.cancellation_confirmation_pdf:
                raise ContractConflict('Existing cancellation PDF is not available')
        result['pdf'] = 'ready'
    except Exception:
        logger.warning('Existing cancellation PDF needs follow-up for case %s', case_id)
    # No email send happens while the PDF transaction is open.
    trip.refresh_from_db()
    recipient = trip.passenger.user if trip.passenger_id else case.requested_by
    if result['pdf'] == 'ready' and recipient and recipient.email:
        try:
            send_passenger_trip_cancellation_to_passenger(recipient, trip)
            result['passenger_email'] = 'requested'
        except Exception:
            result['passenger_email'] = 'review_required'
            logger.warning('Existing passenger cancellation email needs follow-up for case %s', case_id)
    else:
        result['passenger_email'] = 'review_required'
    try:
        send_passenger_trip_cancellation_to_admin(trip)
        result['admin_email'] = 'requested'
    except Exception:
        result['admin_email'] = 'review_required'
        logger.warning('Existing admin cancellation email needs follow-up for case %s', case_id)
    if 'review_required' in result.values():
        logger.warning('Cancellation communication follow-up required for case %s', case_id)
    return result
