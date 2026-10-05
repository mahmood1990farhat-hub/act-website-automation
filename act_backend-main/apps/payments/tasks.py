import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.trips.models import Trip
from apps.trips.services.booking_confirmation import ensure_booking_confirmation_pdf
from utils.common.email import send_internal_notification, send_passenger_confirmation


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=8,
)
def deliver_paid_booking_confirmations(self, trip_id):
    """Generate the PDF and deliver each booking email once per recorded state.

    SMTP acceptance is recorded only after Django's synchronous send_mail returns
    successfully. A retry can therefore continue from whichever delivery remains.
    """
    with transaction.atomic():
        trip = (
            Trip.objects.select_for_update()
            .select_related("passenger__user", "car_type")
            .get(id=trip_id)
        )

        if not trip.is_paid:
            raise ValueError(f"Trip {trip_id} is not paid; refusing paid confirmation")

        if not trip.booking_confirmation_pdf:
            ensure_booking_confirmation_pdf(trip)
            trip.refresh_from_db(fields=["booking_confirmation_pdf"])
        if not trip.booking_confirmation_pdf:
            raise RuntimeError(f"Booking PDF was not persisted for trip {trip_id}")

        passenger_user = trip.passenger.user if trip.passenger and trip.passenger.user else None

        if not trip.passenger_confirmation_sent_at:
            if not send_passenger_confirmation(passenger_user, trip, send_now=True):
                raise RuntimeError(f"Passenger confirmation SMTP send failed for trip {trip_id}")
            trip.passenger_confirmation_sent_at = timezone.now()
            trip.save(update_fields=["passenger_confirmation_sent_at"])
            logger.info("[BOOKING CONFIRMATION] Passenger email accepted for trip %s", trip_id)

        if not trip.internal_booking_notification_sent_at:
            if not send_internal_notification(trip, send_now=True):
                raise RuntimeError(f"Internal booking notification SMTP send failed for trip {trip_id}")
            trip.internal_booking_notification_sent_at = timezone.now()
            trip.save(update_fields=["internal_booking_notification_sent_at"])
            logger.info("[BOOKING CONFIRMATION] Internal email accepted for trip %s", trip_id)

    return {
        "trip_id": trip_id,
        "passenger_confirmation_sent": True,
        "internal_notification_sent": True,
        "pdf_ready": True,
    }
