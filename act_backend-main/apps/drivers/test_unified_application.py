"""Bounded tests of a one-form driver application without real drivers/emails."""
from datetime import date, timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.drivers.models import (
    BaseDriver, NormalDriver, DriverOnboardingRequest,
    DriverApplicationDocument, UnifiedDriverApplication,
)
from apps.vehicle.models import VehicleType

User = get_user_model()
TOKEN = "A" * 48


def pdf(name):
    return SimpleUploadedFile(
        name, b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF", content_type="application/pdf",
    )


def picture(name):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(90, 70, 20)).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class UnifiedOnboardingTests(TestCase):
    def setUp(self):
        cache.clear()
        private = TemporaryDirectory()
        self.addCleanup(private.cleanup)
        public = TemporaryDirectory()
        self.addCleanup(public.cleanup)
        self.private_override = override_settings(
            ACT_DRIVER_PRIVATE_UPLOAD_ROOT=private.name,
            MEDIA_ROOT=public.name,
            DEFAULT_FROM_EMAIL="info@example.invalid",
        )
        self.private_override.enable()
        self.addCleanup(self.private_override.disable)
        self.client = APIClient()
        self.apply_url = "/api/drivers/onboarding/apply/"
        self.setup_url = "/api/drivers/onboarding/set-password/"
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.invalid",
            password="not-a-live-password", account_type="normal",
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.vehicle_type = VehicleType.objects.create(
            code="comfort", name_en="Comfort Class", name_ar="Comfort Class",
            icon="vehicle_types/icons/comfort.png", max_passengers_count=4,
        )

    def payload(self, with_vehicle=False):
        values = {
            "first_name": "Example",
            "last_name": "Applicant",
            "date_of_birth": "1990-04-12",
            "phone_number": "+447700900123",
            "email": "newdriver@example.invalid",
            "address": "An example London street",
            "postcode": "SW1A 1AA",
            "pco_badge_number": "TPH123456",
            "pco_badge_expiry": str(date.today() + timedelta(days=365)),
            "years_experience": "5_plus",
            "vehicle_ownership": "phv_owner" if with_vehicle else "do_not_have_a_phv",
            "agrees_policies": "true",
            "dbs_consent": "true",
            "pco_front": pdf("pco_front.pdf"),
            "pco_back": pdf("pco_back.pdf"),
            "dvla_front": pdf("dvla_front.pdf"),
            "dvla_back": pdf("dvla_back.pdf"),
            "driver_photo": picture("driver.png"),
        }
        if with_vehicle:
            values.update({
                "vehicle_class_code": "comfort",
                "vehicle_make": "Volkswagen",
                "vehicle_model": "Passat",
                "vehicle_year": "2025",
                "vehicle_registration": "AB12 CDE",
                "vehicle_colour": "Black",
                "mot_expiry": str(date.today() + timedelta(days=200)),
                "insurance_expiry": str(date.today() + timedelta(days=150)),
                "accepts_pets": "false",
                "mot": pdf("mot.pdf"),
                "insurance": pdf("insurance.pdf"),
                "vehicle_phv": pdf("phv.pdf"),
                "v5c": pdf("v5c.pdf"),
            })
        return values

    def apply(self, with_vehicle=False, values=None):
        raw = values or self.payload(with_vehicle)
        with patch("apps.drivers.views.unified_application._token_pair",
                   return_value=(TOKEN, __import__("hashlib").sha256(TOKEN.encode()).hexdigest())):
            with patch("apps.drivers.views.unified_application.send_mail", return_value=1) as sender:
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(self.apply_url, raw, format="multipart")
        return response, sender

    def test_one_submission_private_documents_and_welcome_link(self):
        response, sent = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "awaiting_vehicle")
        self.assertEqual(User.objects.filter(email="newdriver@example.invalid").count(), 1)
        self.assertEqual(DriverOnboardingRequest.objects.count(), 1)
        self.assertEqual(UnifiedDriverApplication.objects.count(), 1)
        self.assertEqual(DriverApplicationDocument.objects.count(), 5)
        user = User.objects.get(email="newdriver@example.invalid")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_admin_verified)
        self.assertFalse(user.is_profile_completed)
        sent.assert_called_once()
        self.assertIn("/en/driver-password-setup/#", sent.call_args.args[1])
        self.assertIn(TOKEN, sent.call_args.args[1])
        doc = DriverApplicationDocument.objects.first()
        with self.assertRaises(ValueError):
            doc.file.url
        self.assertNotIn(str(settings.MEDIA_ROOT), doc.file.path)
        self.assertTrue(doc.file.storage.exists(doc.file.name))
        self.assertEqual(doc.file_size, doc.file.size)

    def test_bad_files_and_missing_legal_vehicle_evidence_never_create_user(self):
        bad = self.payload()
        bad["pco_front"] = SimpleUploadedFile("lie.pdf", b"<html>fake</html>", content_type="application/pdf")
        response, _ = self.apply(values=bad)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(User.objects.filter(email="newdriver@example.invalid").exists())
        self.assertEqual(DriverApplicationDocument.objects.count(), 0)
        cache.clear()
        missing = self.payload(with_vehicle=True)
        missing.pop("insurance")
        response, _ = self.apply(values=missing)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(UnifiedDriverApplication.objects.count(), 0)

    def test_duplicate_does_not_recreate_user_or_documents(self):
        response, _ = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        cache.clear()
        response, _ = self.apply()
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(User.objects.filter(email="newdriver@example.invalid").count(), 1)
        self.assertEqual(DriverApplicationDocument.objects.count(), 5)

    def test_password_is_single_use_but_never_verifies_driver(self):
        response, _ = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        cache.clear()
        reply = self.client.post(self.setup_url, {
            "token": TOKEN,
            "password": "SomeVeryStrongPassword+2026",
            "confirm_password": "SomeVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(reply.status_code, 200, reply.data)
        user = User.objects.get(email="newdriver@example.invalid")
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.has_usable_password())
        self.assertFalse(user.is_admin_verified)
        self.assertFalse(user.is_profile_completed)
        self.assertEqual(BaseDriver.objects.count(), 0)
        cache.clear()
        replay = self.client.post(self.setup_url, {
            "token": TOKEN, "password": "AnotherVeryStrongPassword+2026",
            "confirm_password": "AnotherVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(replay.status_code, 400)

    def test_old_approval_endpoint_cannot_bypass_unified_review(self):
        response, _ = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        self.client.force_authenticate(user=self.admin)
        stage_one = self.client.post(
            f"/api/drivers/admin/onboarding-requests/{response.data['application_id']}/action/",
            {"action": "approve"}, format="json",
        )
        self.assertEqual(stage_one.status_code, 409)
        self.assertEqual(BaseDriver.objects.count(), 0)

    def test_password_activated_unified_applicant_cannot_use_legacy_driver_completion(self):
        response, _ = self.apply(with_vehicle=True)
        self.assertEqual(response.status_code, 201, response.data)
        cache.clear()
        reply = self.client.post(self.setup_url, {
            "token": TOKEN,
            "password": "SomeVeryStrongPassword+2026",
            "confirm_password": "SomeVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(reply.status_code, 200, reply.data)
        user = User.objects.get(email="newdriver@example.invalid")
        self.client.force_authenticate(user=user)
        for endpoint in (
            "/api/drivers/complete-normal-driver-info/",
            "/api/drivers/onboarding/step2/",
        ):
            denied = self.client.post(endpoint, {}, format="multipart")
            self.assertEqual(denied.status_code, 409, (endpoint, denied.data))
        self.assertEqual(BaseDriver.objects.count(), 0)
        user.refresh_from_db()
        self.assertFalse(user.is_admin_verified)
        self.assertFalse(user.is_profile_completed)

    def test_private_document_download_requires_admin_authorization(self):
        response, _ = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        document = DriverApplicationDocument.objects.first()
        url = f"/api/drivers/admin/unified-documents/{document.id}/"
        anonymous = self.client.get(url)
        self.assertIn(anonymous.status_code, (401, 403))
        self.client.force_authenticate(user=self.admin)
        approved = self.client.get(url)
        self.assertEqual(approved.status_code, 200)
        self.assertIn("attachment", approved["Content-Disposition"].lower())
        self.assertEqual(approved["Cache-Control"], "private, no-store")

    def test_no_vehicle_applicant_is_never_admin_approvable(self):
        response, _ = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        cache.clear()
        activated = self.client.post(self.setup_url, {
            "token": TOKEN,
            "password": "SomeVeryStrongPassword+2026",
            "confirm_password": "SomeVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(activated.status_code, 200)
        self.client.force_authenticate(user=self.admin)
        endpoint = f"/api/drivers/admin/unified-applications/{response.data['application_id']}/decision/"
        decision = self.client.post(endpoint, {
            "action": "approve", "documents_reviewed": True,
            "dbs_cleared": True, "photo_disclosure_consent": True,
        }, format="json")
        self.assertEqual(decision.status_code, 400)
        self.assertEqual(NormalDriver.objects.count(), 0)
        user = User.objects.get(email="newdriver@example.invalid")
        self.assertFalse(user.is_admin_verified)

    def test_full_evidence_approval_creates_only_one_eligible_driver(self):
        response, _ = self.apply(with_vehicle=True)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "pending_verification")
        cache.clear()
        activated = self.client.post(self.setup_url, {
            "token": TOKEN,
            "password": "SomeVeryStrongPassword+2026",
            "confirm_password": "SomeVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(activated.status_code, 200, activated.data)
        self.client.force_authenticate(user=self.admin)
        endpoint = f"/api/drivers/admin/unified-applications/{response.data['application_id']}/decision/"
        with patch("apps.drivers.views.unified_admin.send_mail", return_value=1):
            with self.captureOnCommitCallbacks(execute=True):
                decision = self.client.post(endpoint, {
                    "action": "approve", "documents_reviewed": True,
                    "dbs_cleared": True, "photo_disclosure_consent": True,
                }, format="json")
        self.assertEqual(decision.status_code, 200, decision.data)
        user = User.objects.get(email="newdriver@example.invalid")
        self.assertTrue(user.is_admin_verified)
        self.assertTrue(user.is_profile_completed)
        driver = BaseDriver.objects.get(user=user)
        self.assertEqual(driver.pco_licence_number, "TPH123456")
        self.assertTrue(driver.driver_photo)
        vehicle = NormalDriver.objects.get(driver=driver).vehicle
        self.assertEqual(vehicle.vehicle_number, "AB12 CDE")
        self.assertEqual(vehicle.vehicle_type, self.vehicle_type)
        self.assertEqual(DriverOnboardingRequest.objects.get(user=user).status, "final_approved")
        self.assertEqual(DriverApplicationDocument.objects.count(), 9)
        again = self.client.post(endpoint, {
            "action": "approve", "documents_reviewed": True,
            "dbs_cleared": True, "photo_disclosure_consent": True,
        }, format="json")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(NormalDriver.objects.count(), 1)
