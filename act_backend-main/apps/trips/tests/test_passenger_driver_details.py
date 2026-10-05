from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PassengerDriverDetailsPresentationTests(SimpleTestCase):
    def test_driver_details_email_contains_required_identity(self):
        html = render_to_string(
            "emails/trip_driver_details_passenger.html",
            {
                "first_name": "Passenger",
                "driver_name": "Alex",
                "driver_phone": "+447700900000",
                "driver_licence_number": "TPH123456",
                "driver_photo_url": "https://assets.example.invalid/driver.jpg",
                "vehicle_name": "Mercedes-Benz E-Class",
                "vehicle_registration": "AB12 CDE",
                "vehicle_color": "Black",
                "support_phone_primary": "+44 7464 940000",
                "support_phone_secondary": "+44 20 8153 0303",
                "support_email": "info@airportandcitytransfer.com",
                "support_website": "https://airportandcitytransfer.com/en",
                "footer_logo_image_url": "",
            },
        )
        for expected in (
            "Alex",
            "TPH123456",
            "driver.jpg",
            "Mercedes-Benz E-Class",
            "AB12 CDE",
            "Black",
            "+44 7464 940000",
        ):
            self.assertIn(expected, html)
        self.assertNotIn("Email Preview Mockups", html)
