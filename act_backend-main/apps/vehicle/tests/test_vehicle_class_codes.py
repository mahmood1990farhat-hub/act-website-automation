from datetime import time

from django.test import SimpleTestCase

from apps.vehicle.catalog import (
    VEHICLE_LUGGAGE_PATTERNS,
    canonical_vehicle_code,
    vehicle_accepts_luggage,
)
from utils.calculate_cost import PRICING, calculate_trip_cost


class VehicleClassCodeTests(SimpleTestCase):
    def test_legacy_names_resolve_to_stable_codes(self):
        expected = {
            "Standard PHV": "comfort",
            "7 Seaters PHV": "comfort_xl",
            "Luxury": "executive",
            "Luxury Van": "executive_xl",
            "VIP Business PHV": "first_class",
        }
        for old_name, code in expected.items():
            self.assertEqual(canonical_vehicle_code(old_name), code)
            self.assertIn(code, PRICING)

    def test_professional_names_resolve_to_same_codes(self):
        expected = {
            "Comfort Class": "comfort",
            "Comfort XL": "comfort_xl",
            "Executive Class": "executive",
            "Executive XL": "executive_xl",
            "First Class": "first_class",
        }
        for display_name, code in expected.items():
            self.assertEqual(canonical_vehicle_code(display_name), code)

    def test_rename_does_not_change_legacy_fare_math(self):
        cases = [
            ("Standard PHV", "comfort"),
            ("7 Seaters PHV", "comfort_xl"),
            ("Luxury", "executive"),
            ("Luxury Van", "executive_xl"),
            ("VIP Business PHV", "first_class"),
        ]
        for old_name, code in cases:
            self.assertEqual(
                calculate_trip_cost(time(14, 0), old_name, 15.0),
                calculate_trip_cost(time(14, 0), code, 15.0),
            )


    def test_approved_luggage_patterns_are_stable(self):
        self.assertEqual(VEHICLE_LUGGAGE_PATTERNS, {
            "comfort": ((2, 2), (0, 4)),
            "comfort_xl": ((3, 3), (4, 0)),
            "executive": ((2, 2), (0, 4)),
            "executive_xl": ((5, 4), (6, 2)),
            "first_class": ((2, 2), (0, 4)),
        })

    def test_luggage_must_fit_one_complete_approved_pattern(self):
        accepted = {
            "comfort": ((2, 2), (0, 4)),
            "comfort_xl": ((3, 3), (4, 0)),
            "executive": ((2, 2), (0, 4)),
            "executive_xl": ((5, 4), (6, 2)),
            "first_class": ((2, 2), (0, 4)),
        }
        for code, patterns in accepted.items():
            for large, small in patterns:
                self.assertTrue(vehicle_accepts_luggage(code, large, small))

        self.assertFalse(vehicle_accepts_luggage("comfort", 1, 3))
        self.assertFalse(vehicle_accepts_luggage("comfort_xl", 4, 1))
        self.assertFalse(vehicle_accepts_luggage("executive_xl", 6, 3))
