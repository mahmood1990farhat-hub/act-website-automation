from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from apps.drivers.models import BaseDriver, NormalDriver
from apps.trips.models import Trip
from apps.trips.tasks.driver_details_reminder import send_driver_details_reminders
from apps.vehicle.models import Vehicle, VehicleType


User = get_user_model()


class DriverDetailsReminderTests(TestCase):
    def test_reminder_is_sent_once_inside_two_hour_window(self):
        user = User.objects.create_user(
            email="driver-reminder@example.invalid",
            username="driver-reminder",
            password="testpass123",
            first_name="Alex",
            account_type="normal_driver",
            address="Test",
        )
        base = BaseDriver.objects.create(
            user=user,
            pco="driver_docs/pco/test.pdf",
            dbs="driver_docs/dbs/test.pdf",
            dvla="driver_docs/dvla/test.pdf",
            pco_licence_number="TPH123456",
            driver_photo="driver_docs/photos/test.jpg",
        )
        vehicle_type = VehicleType.objects.create(
            code="comfort-reminder",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/test.png",
            max_passengers_count=4,
        )
        vehicle = Vehicle.objects.create(
            vehicle_number="AB12 CDE",
            make="Mercedes-Benz",
            model="E-Class",
            color="Black",
            mot="vehicles/mot/test.pdf",
            phv="vehicles/phv/test.pdf",
            year_of_manufacture=2025,
            vehicle_type=vehicle_type,
        )
        NormalDriver.objects.create(driver=base, vehicle=vehicle)

        journey_at = timezone.localtime() + timedelta(minutes=119)
        trip = Trip.objects.create(
            pickup_lat=51.47,
            pickup_lng=-0.45,
            dropoff_lat=51.50,
            dropoff_lng=-0.12,
            trip_date=journey_at.date(),
            trip_time=journey_at.time().replace(tzinfo=None),
            car_type=vehicle_type,
            cost="80.00",
            passengers_count=2,
            status="accepted",
            is_paid=True,
            base_driver=base,
            passenger_name="Guest Passenger",
            passenger_email="guest@example.invalid",
            is_guest_checkout=True,
        )

        with patch(
            "apps.trips.tasks.driver_details_reminder.send_trip_accepted_to_passenger",
            return_value=True,
        ) as sender:
            self.assertEqual(send_driver_details_reminders(), 1)
            self.assertEqual(send_driver_details_reminders(), 0)
            sender.assert_called_once()

        trip.refresh_from_db()
        self.assertIsNotNone(trip.driver_details_reminder_sent_at)
