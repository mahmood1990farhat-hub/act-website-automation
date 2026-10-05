from datetime import datetime, timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.trips.models import Trip
from utils.common.email import send_trip_accepted_to_passenger


@shared_task(name="trips.tasks.send_driver_details_reminders")
def send_driver_details_reminders():
    """Send the confirmed driver details once when a journey is within two hours."""
    now = timezone.now()
    sent = 0
    candidates = Trip.objects.filter(
        status__in=["accepted", "driver_on_the_way"],
        driver_details_reminder_sent_at__isnull=True,
    ).select_related(
        "passenger__user",
        "base_driver__user",
        "base_driver__normal_driver__vehicle__vehicle_type",
        "guest_driver_car",
    )

    for trip in candidates:
        journey_at = timezone.make_aware(datetime.combine(trip.trip_date, trip.trip_time))
        until_journey = journey_at - now
        if until_journey < timedelta(0) or until_journey > timedelta(hours=2):
            continue

        passenger_user = trip.passenger.user if trip.passenger else None
        if trip.is_guest_driver:
            car = trip.guest_driver_car
            guest_info = {
                "name": trip.guest_driver_name,
                "phone": trip.guest_driver_phone,
                "licence_number": trip.guest_driver_licence_number,
                "photo_url": trip.guest_driver_photo_url,
                "car": {
                    "brand_model": f"{car.brand} {car.model}".strip() if car else "",
                    "registration_number": car.registration_number if car else "",
                    "color": car.color if car else "",
                },
            }
            queued = send_trip_accepted_to_passenger(
                passenger_user,
                trip,
                is_guest_driver=True,
                guest_driver_info=guest_info,
            )
        elif trip.base_driver_id:
            queued = send_trip_accepted_to_passenger(
                passenger_user,
                trip,
                trip.base_driver.user,
            )
        else:
            continue

        if queued:
            with transaction.atomic():
                updated = Trip.objects.filter(
                    id=trip.id,
                    driver_details_reminder_sent_at__isnull=True,
                ).update(driver_details_reminder_sent_at=timezone.now())
                sent += updated

    return sent
