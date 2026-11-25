import time
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.trips.services.route_preview import (
    MAX_STOPS, PROOF_TTL_SECONDS, preview_route_arguments, read_route_proof,
)
from apps.vehicle.models import VehicleType


ROUTE = {
    'pickup_location': {'lat': 51.41, 'lng': -0.36},
    'dropoff_location': {'lat': 51.40, 'lng': -0.35},
}
STOPS = [
    {'point_lat': 51.407, 'point_lng': -0.359},
    {'point_lat': 51.406, 'point_lng': -0.352},
]
GOOGLE_ROUTE = [{
    'overview_polyline': {'points': '_p~iF~ps|U_ulLnnqC'},
    'legs': [{'distance': {'value': 1609}, 'duration': {'value': 300}}],
}]
ISOLATED_CACHE = {'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'act-route-preview-tests',
}}
DIRECTIONS = 'utils.common.google_map._google_maps_client'


@override_settings(ROOT_URLCONF='apps.trips.urls', CACHES=ISOLATED_CACHE)
class RoutePreviewTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.directions = self.enterContext(patch(DIRECTIONS)).return_value.directions
        self.directions.return_value = GOOGLE_ROUTE

    def test_selected_points_and_ordered_stops_are_enough(self):
        payload = {**ROUTE, 'stop_points': STOPS}
        result = self.api.post('/route-preview/', payload, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['route_polyline'], GOOGLE_ROUTE[0]['overview_polyline']['points'])
        self.assertEqual(result.data['distance_miles'], 1.0)
        self.assertEqual(result.data['duration_minutes'], 5)
        self.assertIn('no-store', result['Cache-Control'])
        self.assertIn('/api/trips/route-preview/', settings.SILKY_IGNORE_PATHS)
        self.assertNotIn('car_type', result.data)
        args = self.directions.call_args.kwargs
        self.assertEqual(args['waypoints'], [(stop['point_lat'], stop['point_lng']) for stop in STOPS])
        self.assertEqual(args['mode'], 'driving')
        self.assertFalse(args['optimize_waypoints'])

    def test_rejects_unselected_or_invalid_locations_before_google(self):
        for payload in (
            {}, {**ROUTE, 'pickup_location': {'description': 'Somewhere'}},
            {**ROUTE, 'dropoff_location': {'lat': 0, 'lng': 0}},
            {**ROUTE, 'pickup_location': {'lat': True, 'lng': -0.2}},
            {**ROUTE, 'pickup_location': {'lat': 91, 'lng': -0.2}},
            {**ROUTE, 'stop_points': [{'point_lat': 51.4, 'point_lng': 181}]},
            {**ROUTE, 'stop_points': STOPS[:1] * (MAX_STOPS + 1)},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.api.post('/route-preview/', payload, format='json').status_code, 400)
        for invalid in (float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                preview_route_arguments({**ROUTE, 'pickup_location': {'lat': invalid, 'lng': 0}})
        self.directions.assert_not_called()

    def test_provider_failure_keeps_details_out_of_public_response(self):
        self.directions.side_effect = RuntimeError('sensitive-provider-diagnostic')
        result = self.api.post('/route-preview/', ROUTE, format='json')
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.data, {'code': 'route_preview_unavailable'})
        self.assertIn('no-store', result['Cache-Control'])

    def test_preview_rate_limit_runs_before_google(self):
        with patch('apps.trips.views.route_preview.RoutePreviewThrottle.rate', '1/min'):
            self.assertEqual(self.api.post('/route-preview/', ROUTE, format='json').status_code, 200)
            result = self.api.post('/route-preview/', ROUTE, format='json', HTTP_X_FORWARDED_FOR='203.0.113.2, 127.0.0.1')
            self.assertEqual(result.status_code, 429)
        self.directions.assert_called_once()

    def test_proof_binds_the_ordered_route_and_expires(self):
        now = time.time()
        payload = {**ROUTE, 'stop_points': STOPS}
        with patch('django.core.signing.time.time', return_value=now):
            result = self.api.post('/route-preview/', payload, format='json')
        proof = result.data['route_proof']
        self.assertEqual(read_route_proof({**payload, 'route_proof': proof})['distance_meters'], 1609)
        for changed in (
            {**payload, 'pickup_location': ROUTE['dropoff_location']},
            {**payload, 'stop_points': list(reversed(STOPS))},
            {**payload, 'stop_points': STOPS[:1]},
        ):
            self.assertIsNone(read_route_proof({**changed, 'route_proof': proof}))
        with patch('django.core.signing.time.time', return_value=now + PROOF_TTL_SECONDS + 1):
            self.assertIsNone(read_route_proof({**payload, 'route_proof': proof}))


@override_settings(ROOT_URLCONF='apps.trips.urls', CACHES=ISOLATED_CACHE)
class RoutePreviewQuoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        VehicleType.objects.create(code='comfort', name_en='Comfort', name_ar='Comfort', max_passengers_count=4)

    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.directions = self.enterContext(patch(DIRECTIONS)).return_value.directions
        self.directions.return_value = GOOGLE_ROUTE
        self.prices = self.enterContext(patch(
            'apps.trips.views.calculate_trip_cost.calculate_total_cost',
            return_value=tuple(map(Decimal, ('40', '0', '0', '40', '0'))),
        ))
        self.enterContext(patch(
            'apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport',
            return_value={'pickup_airport': None, 'dropoff_airport': None},
        ))
        self.quote = {**ROUTE, 'trip_date': '2035-01-01', 'trip_time': '10:00', 'passengers_count': 1}

    def test_normal_quote_reuses_preview_once_and_prices_server_side(self):
        response = self.api.post('/route-preview/', ROUTE, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        payload = {
            **self.quote, 'route_proof': response.data['route_proof'],
            'distance_miles': 0.01, 'duration_minutes': 999, 'route_polyline': 'untrusted',
        }
        quote = self.api.post('/calculate-trip-cost/', payload, format='json')
        self.assertEqual(quote.status_code, 200, quote.data)
        self.assertEqual(quote.data['distance_miles'], 1.0)
        self.assertEqual(quote.data['expected_trip_duration_minutes'], 5)
        self.assertEqual(quote.data['route_polyline'], response.data['route_polyline'])
        self.assertEqual(self.prices.call_args.args[2], 1.0)
        self.directions.assert_called_once()
        self.assertNotIn('route_proof', quote.data)

    def test_legacy_mismatched_tampered_and_expired_proofs_use_normal_road_lookup(self):
        preview = self.api.post('/route-preview/', {**ROUTE, 'stop_points': STOPS}, format='json')
        proof = preview.data['route_proof']
        with patch('django.core.signing.time.time', return_value=time.time() - PROOF_TTL_SECONDS - 10):
            expired = self.api.post('/route-preview/', ROUTE, format='json').data['route_proof']
        for supplied in ({}, {'route_proof': proof}, {'route_proof': proof + 'x'}, {'route_proof': expired}):
            self.directions.reset_mock()
            with self.subTest(keys=list(supplied)):
                quote = self.api.post('/calculate-trip-cost/', {**self.quote, **supplied}, format='json')
                self.assertEqual(quote.status_code, 200, quote.data)
                self.assertEqual(quote.data['distance_miles'], 1.0)
                self.directions.assert_called_once()
