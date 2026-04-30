from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _

from apps.pricing.services.airport_resolver import AirportResolver


def prepare_trip_data(data, locale='en'):
    """
    Prepare trip data from pickup_location and dropoff_location.
    Airport is never sent as airport_id; it is detected from coordinates
    using each airport's detection_area (polygon).
    """
    pickup = data.pop("pickup_location", {})
    dropoff = data.pop("dropoff_location", {})

    missing = []
    if "lat" not in pickup or "lng" not in pickup:
        missing.append("pickup_location")
    if "lat" not in dropoff or "lng" not in dropoff:
        missing.append("dropoff_location")
    if missing:
        raise ValidationError({
            f: _("Coordinates (lat, lng) required.") for f in missing
        })

    pickup_lat = float(pickup["lat"])
    pickup_lng = float(pickup["lng"])
    dropoff_lat = float(dropoff["lat"])
    dropoff_lng = float(dropoff["lng"])

    data.update(
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        dropoff_lat=dropoff_lat,
        dropoff_lng=dropoff_lng,
    )

    if pickup.get("address") or pickup.get("str"):
        data["pickup_str"] = pickup.get("address") or pickup.get("str")
    if dropoff.get("address") or dropoff.get("str"):
        data["dropoff_str"] = dropoff.get("address") or dropoff.get("str")

    return data
