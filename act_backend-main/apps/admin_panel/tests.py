from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from apps.admin_panel.serializers.trips import TripWithStopPointSerializer
from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


class AdminPaidBookingSnapshotTests(TestCase):
    def setUp(self):
        self.vehicle = VehicleType.objects.create(
            code="comfort",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/admin-test.png",
            max_passengers_count=4,
            order=1,
        )

    def test_paid_guest_booking_exposes_operational_admin_snapshot(self):
        trip = Trip.objects.create(
            pickup_lat=51.47,
            pickup_lng=-0.45,
            dropoff_lat=51.50,
            dropoff_lng=-0.12,
            pickup_str="Heathrow Airport",
            dropoff_str="Central London",
            trip_date=date(2030, 1, 1),
            trip_time=time(12, 0),
            car_type=self.vehicle,
            cost=Decimal("85.50"),
            passengers_count=2,
            passenger_name="Guest Passenger",
            passenger_email="guest@example.invalid",
            passenger_country_code="+44",
            passenger_phone="7700900000",
            is_guest_checkout=True,
            large_suitcase=2,
            small_suitcase=2,
            stripe_payment_intent="pi_admin_acceptance",
            card_brand="visa",
            last4="4242",
            is_paid=True,
        )

        data = TripWithStopPointSerializer(trip).data

        self.assertEqual(data["passenger_info"]["full_name"], "Guest Passenger")
        self.assertEqual(data["passenger_info"]["email"], "guest@example.invalid")
        self.assertEqual(data["vehicle_info"]["code"], "comfort")
        self.assertEqual(data["vehicle_info"]["name"], "Comfort Class")
        self.assertTrue(data["payment_info"]["is_paid"])
        self.assertEqual(data["payment_info"]["payment_intent_id"], "pi_admin_acceptance")
        self.assertEqual(data["payment_info"]["amount"], "85.50")
        self.assertEqual(data["large_suitcase"], 2)
        self.assertEqual(data["small_suitcase"], 2)
        self.assertEqual(data["pickup_str"], "Heathrow Airport")
        self.assertEqual(data["dropoff_str"], "Central London")
