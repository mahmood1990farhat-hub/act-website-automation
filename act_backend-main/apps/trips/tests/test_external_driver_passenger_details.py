from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


User = get_user_model()


class ExternalDriverPassengerDetailsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="external-admin@example.invalid",
            username="external-admin",
            password="testpass123",
            account_type="admin",
            address="Test",
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        vehicle_type = VehicleType.objects.create(
            code="comfort-external",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/test.png",
            max_passengers_count=4,
        )
        self.trip = Trip.objects.create(
            pickup_lat=51.47,
            pickup_lng=-0.45,
            dropoff_lat=51.50,
            dropoff_lng=-0.12,
            trip_date=date.today() + timedelta(days=1),
            trip_time=time(12, 0),
            car_type=vehicle_type,
            cost="80.00",
            passengers_count=2,
            status="pending",
            is_paid=True,
            passenger_name="Guest Passenger",
            passenger_email="guest@example.invalid",
            is_guest_checkout=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_external_assignment_requires_and_emails_passenger_identity(self):
        payload = {
            "guest_driver_name": "Alex Driver",
            "guest_driver_phone": "+447700900000",
            "guest_driver_company": "Partner Operator",
            "guest_driver_licence_number": "TPH654321",
            "guest_driver_photo_url": "https://partner.example.invalid/driver.jpg",
            "car_info": {
                "brand": "Mercedes-Benz",
                "model": "E-Class",
                "color": "Black",
                "registration_number": "AB12 CDE",
            },
        }
        with patch(
            "utils.common.email.send_trip_accepted_to_passenger",
            return_value=True,
        ) as sender:
            response = self.client.post(
                f"/api/admin-panel/trips/{self.trip.id}/assign-guest-driver/",
                payload,
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.guest_driver_licence_number, "TPH654321")
        self.assertEqual(
            self.trip.guest_driver_photo_url,
            "https://partner.example.invalid/driver.jpg",
        )
        sender.assert_called_once()
        self.assertIsNone(sender.call_args.args[0])
        guest = sender.call_args.kwargs["guest_driver_info"]
        self.assertEqual(guest["licence_number"], "TPH654321")
        self.assertEqual(guest["car"]["registration_number"], "AB12 CDE")

    def test_external_assignment_rejects_missing_passenger_identity(self):
        response = self.client.post(
            f"/api/admin-panel/trips/{self.trip.id}/assign-guest-driver/",
            {
                "guest_driver_name": "Alex Driver",
                "guest_driver_phone": "+447700900000",
                "car_info": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
