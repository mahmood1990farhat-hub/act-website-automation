import googlemaps
from django.conf import settings
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _
from googlemaps.convert import decode_polyline
import requests

GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def get_route_with_distance(pickup_lat, pickup_lng,
                            dropoff_lat, dropoff_lng,
                            stop_points=None):
    stop_points = stop_points or []
    origin      = (pickup_lat, pickup_lng)
    destination = (dropoff_lat, dropoff_lng)
    waypoints   = [(p["point_lat"], p["point_lng"]) for p in stop_points]

    # 1)  Ask for alternatives
    directions_result = gmaps.directions(
        origin=origin,
        destination=destination,
        waypoints=waypoints,
        optimize_waypoints=False,
        mode="driving",
        units="metric",
        alternatives=True          # <-- NEW
    )
    # print("directions_result",directions_result)

    if not directions_result:
        raise ValidationError({"details": _("No route found")})

    # 2)  Pick shortest route (smallest total distance)
    def total_distance(route):
        return sum(leg['distance']['value'] for leg in route['legs'])

    route = min(directions_result, key=total_distance)
    # print("route",route)

    total_distance_meters = total_distance(route)
    total_duration_seconds = sum(leg['duration']['value'] for leg in route['legs'])

    return {
        "route_polyline": route['overview_polyline']['points'],
        "distance_meters": total_distance_meters,
        "distance_miles": round(total_distance_meters / 1609.34, 2),
        "duration_minutes": round(total_duration_seconds / 60)
    }


def reverse_geocode(lat, lng, locale='en'):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": GOOGLE_MAPS_API_KEY,
        "language": locale
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        return None

    result = data["results"][0]
    place_id = result.get("place_id")
    formatted_address = result.get("formatted_address")
    postal_code = None

    for component in result.get("address_components", []):
        if "postal_code" in component["types"]:
            postal_code = component["long_name"]
            break

    return {
        "place_id": place_id,
        "formatted_address": formatted_address,
        "postal_code": postal_code
    }


# -------------  NEW  -------------
def place_to_string(place_id: str | None, fallback: str | None = None) -> str:
    """
    Return a short human-readable name for a Google place_id.
    Falls back to `fallback` (pickup_str / dropoff_str) if place_id is empty
    or if the API call fails.
    """
    if not place_id:
        return fallback or ""

    try:
        details = gmaps.place(place_id=place_id, fields=["name", "formatted_address"])
        result = details.get("result", {})
        name = result.get("name", "")
        addr = result.get("formatted_address", "")
        out = f"{name}, {addr}" if name and addr else (name or addr)
        return out or fallback or ""
    except Exception:
        return fallback or ""