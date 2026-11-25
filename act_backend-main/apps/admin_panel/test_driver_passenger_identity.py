"""Admin correction of genuine passenger-facing identity for existing ACT drivers."""
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.drivers.models import BaseDriver, NormalDriver
from apps.vehicle.models import Vehicle, VehicleType


User = get_user_model()


def _photo():
    buffer = BytesIO()
    Image.new("RGB", (24, 24), color=(32, 64, 96)).save(buffer, format="PNG")
    return SimpleUploadedFile("verified-driver.png", buffer.getvalue(), content_type="image/png")


class DriverPassengerIdentityAdminTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.admin = User.objects.create_user(
            username="identity-admin", email="admin@example.invalid",
            password="test-only", account_type="admin", address="Test",
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()

        user = User.objects.create_user(
            username="identity-driver", email="driver@example.invalid",
            password="test-only", account_type="normal_driver", address="Test",
        )
        user.is_active = True
        user.is_profile_completed = True
        user.is_admin_verified = True
        user.save()
        self.user = user
        self.base_driver = BaseDriver.objects.create(
            user=user,
            pco="driver_docs/pco/verified.pdf",
            dbs="driver_docs/dbs/verified.pdf",
            dvla="driver_docs/dvla/verified.pdf",
            pco_licence_number="",
        )
        self.vehicle_type = VehicleType.objects.create(
            code="comfort",
            name_en="Comfort Class",
            name_ar="Comfort Class",
            icon="vehicle_types/icons/comfort.png",
            max_passengers_count=4,
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_number="AB12 CDE",
            make="", model="", color="",
            mot="vehicles/mot/verified.pdf",
            year_of_manufacture=2025,
            phv="vehicles/phv/verified.pdf",
            vehicle_type=self.vehicle_type,
        )
        self.normal_driver = NormalDriver.objects.create(
            driver=self.base_driver, vehicle=self.vehicle,
        )
        self.url = f"/api/admin-panel/drivers/{self.normal_driver.pk}/update/"
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_authenticated_admin_saves_real_driver_identity_and_vehicle(self):
        response = self.client.patch(self.url, {
            "pco_licence_number": "TPH987654",
            "vehicle_make": "Volkswagen",
            "vehicle_model": "Passat",
            "vehicle_color": "Blue",
            "driver_photo": _photo(),
        }, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.base_driver.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.base_driver.pco_licence_number, "TPH987654")
        self.assertTrue(self.base_driver.driver_photo.name.startswith("driver_docs/photos/"))
        self.assertEqual((self.vehicle.make, self.vehicle.model, self.vehicle.color),
                         ("Volkswagen", "Passat", "Blue"))
        self.assertEqual(self.vehicle.vehicle_number, "AB12 CDE")
        self.assertEqual(self.vehicle.vehicle_type_id, self.vehicle_type.pk)
        self.assertEqual(response.data["data"]["vehicle"]["make"], "Volkswagen")
        self.assertEqual(response.data["data"]["vehicle"]["model"], "Passat")
        self.assertEqual(response.data["data"]["vehicle"]["color"], "Blue")
        self.assertEqual(response.data["data"]["driver"]["pco_licence_number"], "TPH987654")

    def test_omitted_photo_and_licence_keep_verified_existing_values(self):
        self.base_driver.pco_licence_number = "TPH111222"
        self.base_driver.driver_photo = "driver_docs/photos/already-verified.jpg"
        self.base_driver.save(update_fields=["pco_licence_number", "driver_photo"])
        response = self.client.patch(self.url, {
            "vehicle_make": "BMW",
            "vehicle_model": "5 Series",
            "vehicle_color": "Black",
        }, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.base_driver.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.base_driver.pco_licence_number, "TPH111222")
        self.assertEqual(self.base_driver.driver_photo.name, "driver_docs/photos/already-verified.jpg")
        self.assertEqual(self.vehicle.make, "BMW")

    def test_non_admin_cannot_modify_driver_documents(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {
            "pco_licence_number": "TPH000000",
            "vehicle_make": "Wrong",
            "driver_photo": _photo(),
        }, format="multipart")
        self.assertIn(response.status_code, (401, 403), response.data)
        self.base_driver.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.base_driver.pco_licence_number, "")
        self.assertEqual(self.vehicle.make, "")
        self.assertFalse(self.base_driver.driver_photo)

    def test_invalid_driver_photo_fails_without_writing_vehicle(self):
        response = self.client.patch(self.url, {
            "vehicle_make": "Not Persisted",
            "driver_photo": SimpleUploadedFile(
                "fake.png", b"not an image", content_type="image/png",
            ),
        }, format="multipart")
        self.assertEqual(response.status_code, 400, response.data)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.make, "")
        self.base_driver.refresh_from_db()
        self.assertFalse(self.base_driver.driver_photo)

    def test_original_documents_and_vehicle_class_are_preserved(self):
        response = self.client.patch(self.url, {
            "pco_licence_number": "TPH002244",
            "vehicle_make": "Mercedes-Benz",
        }, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.base_driver.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.base_driver.pco.name, "driver_docs/pco/verified.pdf")
        self.assertEqual(self.base_driver.dbs.name, "driver_docs/dbs/verified.pdf")
        self.assertEqual(self.base_driver.dvla.name, "driver_docs/dvla/verified.pdf")
        self.assertEqual(self.vehicle.vehicle_type_id, self.vehicle_type.id)
        self.assertEqual(self.vehicle.vehicle_number, "AB12 CDE")
