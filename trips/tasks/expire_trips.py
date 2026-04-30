from celery import shared_task
from django.utils import timezone
from datetime import datetime
from ..models import Trip


@shared_task
def expire_old_trips():
    now = timezone.now()

    trips = Trip.objects.filter(
        status="pending"
    )

    expired_ids = []

    for trip in trips:
        trip_datetime = timezone.make_aware(
            datetime.combine(trip.trip_date, trip.trip_time)
        )

        if trip_datetime < now:
            expired_ids.append(trip.id)

    if expired_ids:
        Trip.objects.filter(id__in=expired_ids).update(status="expired")

    return f"{len(expired_ids)} trips expired"