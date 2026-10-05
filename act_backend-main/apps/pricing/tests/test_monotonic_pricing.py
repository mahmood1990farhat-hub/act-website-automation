from datetime import time
from decimal import Decimal

from django.test import SimpleTestCase

from utils.calculate_cost import calculate_trip_cost


class LegacyPricingMonotonicityTests(SimpleTestCase):
    def test_longer_trip_never_drops_at_distance_band_boundaries(self):
        for vehicle_code in (
            "comfort",
            "comfort_xl",
            "executive",
            "executive_xl",
            "first_class",
        ):
            for trip_time in (time(14, 0), time(8, 0)):
                previous = None
                # Check immediately around every configured 10-mile boundary.
                for tenths in range(1, 900):
                    distance = tenths / 10
                    cost = Decimal(str(calculate_trip_cost(
                        trip_time,
                        vehicle_code,
                        distance,
                    )))
                    if previous is not None:
                        self.assertGreaterEqual(
                            cost,
                            previous,
                            f"{vehicle_code} became cheaper at {distance} miles",
                        )
                    previous = cost

    def test_reported_40_to_41_mile_pattern_cannot_decrease(self):
        forty = calculate_trip_cost(time(14, 0), "comfort", 40)
        forty_one = calculate_trip_cost(time(14, 0), "comfort", 41)

        self.assertGreaterEqual(forty_one, forty)
