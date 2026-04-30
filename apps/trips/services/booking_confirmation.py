import logging
from django.core.files.base import ContentFile
from apps.trips.services.pdf_generator import (
    generate_booking_confirmation_pdf,
    generate_cancellation_confirmation_pdf,
)


logger = logging.getLogger(__name__)


def ensure_booking_confirmation_pdf(trip):
    """
    Generate and attach booking confirmation PDF once trip is accepted.
    Safe to call multiple times; skips if file already exists.
    """
    if trip.booking_confirmation_pdf:
        return False

    resolved_payment_method = trip.card_brand or "Card Payment"
    pdf_buffer = generate_booking_confirmation_pdf(
        trip,
        payment_method=resolved_payment_method
    )
    filename = f"booking_confirmation_trip_{trip.id}.pdf"
    trip.booking_confirmation_pdf.save(
        filename,
        ContentFile(pdf_buffer.read()),
        save=True
    )
    return True


def ensure_cancellation_confirmation_pdf(trip):
    """
    Generate and attach cancellation confirmation PDF once trip is cancelled.
    Safe to call multiple times; skips if file already exists.
    """
    if trip.cancellation_confirmation_pdf:
        return False

    resolved_payment_method = trip.card_brand or "Card Payment"
    pdf_buffer = generate_cancellation_confirmation_pdf(
        trip,
        payment_method=resolved_payment_method
    )
    filename = f"cancellation_confirmation_trip_{trip.id}.pdf"
    trip.cancellation_confirmation_pdf.save(
        filename,
        ContentFile(pdf_buffer.read()),
        save=True
    )
    return True

