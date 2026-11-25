"""A short-lived, signed road route can be reused by the subsequent fare quote."""

import hashlib
import json

from django.core import signing


# Preview uses the Directions waypoint ceiling. Existing quote requests keep their own rules.
MAX_STOPS = 25
PROOF_TTL_SECONDS = 10 * 60
MAX_PROOF_LENGTH = 65536
SIGNING_SALT = 'act.trip-route-preview.v1'
ROUTE_FIELDS = ('route_polyline', 'distance_meters', 'distance_miles', 'duration_minutes')


def _coordinates(point, lat_field, lng_field):
    if not isinstance(point, dict):
        raise ValueError('Invalid location')
    lat, lng = point.get(lat_field), point.get(lng_field)
    if (type(lat) not in (int, float) or type(lng) not in (int, float)
            or not -90 <= lat <= 90 or not -180 <= lng <= 180 or (lat == 0 and lng == 0)):
        raise ValueError('Invalid coordinates')
    return float(lat), float(lng)


def preview_route_arguments(payload):
    if not isinstance(payload, dict):
        raise ValueError('Invalid route')
    pickup = _coordinates(payload.get('pickup_location'), 'lat', 'lng')
    dropoff = _coordinates(payload.get('dropoff_location'), 'lat', 'lng')
    stops = payload.get('stop_points', [])
    if not isinstance(stops, list) or len(stops) > MAX_STOPS:
        raise ValueError('Invalid stops')
    coordinates = [_coordinates(stop, 'point_lat', 'point_lng') for stop in stops]
    return {
        'pickup_lat': pickup[0], 'pickup_lng': pickup[1],
        'dropoff_lat': dropoff[0], 'dropoff_lng': dropoff[1],
        'stop_points': [{'point_lat': lat, 'point_lng': lng} for lat, lng in coordinates],
    }


def _route_fingerprint(arguments):
    encoded = json.dumps(arguments, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('ascii')).hexdigest()


def sign_route(arguments, route):
    fields = {key: route[key] for key in ROUTE_FIELDS}
    return signing.dumps([_route_fingerprint(arguments), fields], salt=SIGNING_SALT, compress=True)


def read_route_proof(payload):
    if not isinstance(payload, dict):
        return None
    proof = payload.get('route_proof')
    if not isinstance(proof, str) or not proof.isascii() or len(proof) > MAX_PROOF_LENGTH or not proof:
        return None
    try:
        fingerprint, route = signing.loads(proof, salt=SIGNING_SALT, max_age=PROOF_TTL_SECONDS)
        if fingerprint == _route_fingerprint(preview_route_arguments(payload)):
            return route
    except (signing.BadSignature, ValueError):
        pass
    return None
