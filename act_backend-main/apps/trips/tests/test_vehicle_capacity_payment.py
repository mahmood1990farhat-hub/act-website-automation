from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from apps.trips.views.initiate_payment import validate_vehicle_capacity


class VehicleCapacityPaymentTests(SimpleTestCase):
    def test_supported_combination_passes(self):
        vehicle = SimpleNamespace(code="executive_xl", max_passengers_count=7)
        validate_vehicle_capacity({"passengers_count": 7, "large_suitcase": 5, "small_suitcase": 4}, vehicle)

    def test_unsupported_combination_fails(self):
        vehicle = SimpleNamespace(code="comfort", max_passengers_count=4)
        with self.assertRaises(ValidationError):
            validate_vehicle_capacity({"passengers_count": 4, "large_suitcase": 1, "small_suitcase": 3}, vehicle)

    def test_excess_passenger_count_fails(self):
        vehicle = SimpleNamespace(code="comfort", max_passengers_count=4)
        with self.assertRaises(ValidationError):
            validate_vehicle_capacity({"passengers_count": 5, "large_suitcase": 0, "small_suitcase": 0}, vehicle)
