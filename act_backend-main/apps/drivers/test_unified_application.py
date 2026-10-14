"""Bounded tests of a one-form driver application without real drivers/emails."""
import base64
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
    OperatorVehiclePeriod, OperatorVehicleEvidence, OperatorRecordAccessAudit,
)
from apps.vehicle.models import VehicleType

User = get_user_model()
TOKEN = "A" * 48
TEST_OPERATOR_KEY = base64.urlsafe_b64encode(bytes([7]) * 32).decode("ascii")


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
            ACT_NI_ENCRYPTION_KEY=TEST_OPERATOR_KEY,
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
            "passenger_photo_disclosure_consent": "true",
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

    def operator_approval_fields(self):
        return {
            "national_insurance_number": "AB 12 34 56 C",
            "registered_keeper_name": "Synthetic Registered Keeper",
            "registered_keeper_address": "12 Example Road, London",
            "operator_records_checked": True,
        }

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

    def test_adding_vehicle_after_initial_application_does_not_create_second_driver(self):
        application, _ = self.apply()
        self.assertEqual(application.status_code, 201, application.data)
        cache.clear()
        activated = self.client.post(self.setup_url, {
            "token": TOKEN,
            "password": "SomeVeryStrongPassword+2026",
            "confirm_password": "SomeVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(activated.status_code, 200, activated.data)
        user = User.objects.get(email="newdriver@example.invalid")
        self.client.force_authenticate(user=user)
        full = self.payload(with_vehicle=True)
        fields = (
            "vehicle_ownership", "vehicle_class_code", "vehicle_make",
            "vehicle_model", "vehicle_year", "vehicle_registration",
            "vehicle_colour", "mot_expiry", "insurance_expiry",
            "accepts_pets", "mot", "insurance", "vehicle_phv", "v5c",
        )
        addition = {key: full[key] for key in fields}
        response = self.client.post(
            "/api/drivers/onboarding/add-vehicle/",
            addition, format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        profile = UnifiedDriverApplication.objects.get(onboarding_request__user=user)
        self.assertFalse(profile.awaiting_vehicle)
        self.assertEqual(profile.vehicle_registration, "AB12 CDE")
        self.assertEqual(DriverApplicationDocument.objects.count(), 9)
        self.assertEqual(User.objects.filter(email=user.email).count(), 1)
        self.assertFalse(user.is_admin_verified)
        self.assertFalse(user.is_profile_completed)
        self.assertEqual(NormalDriver.objects.count(), 0)

        cache.clear()
        duplicate_values = self.payload(with_vehicle=True)
        duplicate = self.client.post(
            "/api/drivers/onboarding/add-vehicle/",
            {key: duplicate_values[key] for key in fields},
            format="multipart",
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(DriverApplicationDocument.objects.count(), 9)

        self.client.force_authenticate(user=self.admin)
        with patch("apps.drivers.views.unified_admin.send_mail", return_value=1):
            with self.captureOnCommitCallbacks(execute=True):
                approval = self.client.post(
                    "/api/drivers/admin/unified-applications/"
                    f"{application.data['application_id']}/decision/",
                    {
                        "action": "approve", "documents_reviewed": True,
                        "dbs_cleared": True, "photo_disclosure_consent": True,
                    }, format="json",
                )
        self.assertEqual(approval.status_code, 200, approval.data)
        self.assertEqual(NormalDriver.objects.count(), 1)
        user.refresh_from_db()
        self.assertTrue(user.is_admin_verified)
        self.assertTrue(user.is_profile_completed)

    def test_explicit_passenger_photo_disclosure_consent_is_required(self):
        payload = self.payload(with_vehicle=True)
        payload.pop("passenger_photo_disclosure_consent")
        response, _ = self.apply(values=payload)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(UnifiedDriverApplication.objects.count(), 0)
        self.assertFalse(User.objects.filter(email="newdriver@example.invalid").exists())

    def test_admin_requested_corrections_replace_only_allowed_private_files(self):
        created, _ = self.apply(with_vehicle=True)
        self.assertEqual(created.status_code, 201, created.data)
        cache.clear()
        activated = self.client.post(self.setup_url, {
            "token": TOKEN,
            "password": "SomeVeryStrongPassword+2026",
            "confirm_password": "SomeVeryStrongPassword+2026",
        }, format="json")
        self.assertEqual(activated.status_code, 200)
        profile = UnifiedDriverApplication.objects.get(
            onboarding_request__user__email="newdriver@example.invalid"
        )
        original = profile.documents.get(kind="pco_front")
        old_path = original.file.name
        old_file_id = original.pk
        self.client.force_authenticate(user=self.admin)
        endpoint = f"/api/drivers/admin/unified-applications/{created.data['application_id']}/decision/"
        with patch("apps.drivers.views.unified_admin.send_mail", return_value=1):
            with self.captureOnCommitCallbacks(execute=True):
                requested = self.client.post(endpoint, {
                    "action": "request_changes",
                    "reason": "Badge scan unclear; colour entered incorrectly.",
                    "files_to_modify": ["pco_front", "vehicle_colour"],
                }, format="json")
        self.assertEqual(requested.status_code, 200, requested.data)
        profile.onboarding_request.refresh_from_db()
        self.assertEqual(profile.onboarding_request.status, "needs_modification")
        self.assertEqual(profile.onboarding_request.files_need_modification,
                         ["pco_front", "vehicle_colour"])
        self.assertEqual(NormalDriver.objects.count(), 0)
        cache.clear()
        user = profile.onboarding_request.user
        self.client.force_authenticate(user=user)
        corrections_url = "/api/drivers/onboarding/correct/"
        denied = self.client.post(corrections_url, {
            "pco_front": pdf("replacement.pdf"), "vehicle_colour": "Blue",
            "mot": pdf("extra.pdf"),
        }, format="multipart")
        self.assertEqual(denied.status_code, 400, denied.data)
        original.refresh_from_db()
        self.assertEqual(original.file.name, old_path)

        cache.clear()
        with self.captureOnCommitCallbacks(execute=True):
            correct = self.client.post(corrections_url, {
                "pco_front": pdf("replacement.pdf"),
                "vehicle_colour": "Blue",
            }, format="multipart")
        self.assertEqual(correct.status_code, 200, correct.data)
        profile.refresh_from_db()
        profile.onboarding_request.refresh_from_db()
        original.refresh_from_db()
        self.assertEqual(profile.vehicle_colour, "Blue")
        self.assertEqual(profile.onboarding_request.status, "pending")
        self.assertEqual(profile.onboarding_request.files_need_modification, [])
        self.assertEqual(original.pk, old_file_id)
        self.assertNotEqual(original.file.name, old_path)
        self.assertTrue(original.file.storage.exists(original.file.name))
        self.assertFalse(original.file.storage.exists(old_path))
        self.assertEqual(DriverApplicationDocument.objects.count(), 9)
        self.assertFalse(user.is_admin_verified)
        self.assertFalse(user.is_profile_completed)
        self.assertEqual(BaseDriver.objects.count(), 0)

        cache.clear()
        replay = self.client.post(corrections_url, {
            "pco_front": pdf("again.pdf"), "vehicle_colour": "Green",
        }, format="multipart")
        self.assertEqual(replay.status_code, 403)
        profile.refresh_from_db()
        self.assertEqual(profile.vehicle_colour, "Blue")

    def test_private_storage_rejects_symlink_to_public_media(self):
        from django.core.exceptions import ImproperlyConfigured
        from pathlib import Path
        from apps.drivers.models.unified_application import PrivateDriverDocumentStorage
        with TemporaryDirectory() as root:
            public = Path(root) / "public"
            public.mkdir()
            linked = Path(root) / "private-link"
            linked.symlink_to(public, target_is_directory=True)
            with override_settings(
                MEDIA_ROOT=str(public),
                ACT_DRIVER_PRIVATE_UPLOAD_ROOT=str(linked),
            ):
                with self.assertRaises(ImproperlyConfigured):
                    _ = PrivateDriverDocumentStorage().location

    def test_evidence_download_type_is_from_content_not_filename(self):
        values = self.payload()
        values["pco_front"] = pdf("looks-like-an-image.png")
        created, _ = self.apply(values=values)
        self.assertEqual(created.status_code, 201, created.data)
        document = DriverApplicationDocument.objects.get(kind="pco_front")
        self.assertEqual(document.content_type, "application/pdf")
        self.client.force_authenticate(user=self.admin)
        reply = self.client.get(
            f"/api/drivers/admin/unified-documents/{document.pk}/"
        )
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply["Content-Type"], "application/pdf")

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

    def test_first_class_uses_existing_first_class_vehicle_code(self):
        first_class = VehicleType.objects.create(
            code="first_class",
            name_en="First Class",
            name_ar="الدرجة الأولى",
            icon="vehicle_types/icons/first.png",
            max_passengers_count=4,
        )
        application = self.payload(with_vehicle=True)
        application["vehicle_class_code"] = "first_class"
        response, _ = self.apply(values=application)
        self.assertEqual(response.status_code, 201, response.data)
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
                    "action": "approve",
                    "documents_reviewed": True,
                    "dbs_cleared": True,
                    "photo_disclosure_consent": True,
                    **self.operator_approval_fields(),
                }, format="json")
        self.assertEqual(decision.status_code, 200, decision.data)
        driver = BaseDriver.objects.get(user__email="newdriver@example.invalid")
        self.assertEqual(NormalDriver.objects.get(driver=driver).vehicle.vehicle_type, first_class)

    def test_operator_records_must_be_complete_and_encrypted_before_approval(self):
        response, _ = self.apply(with_vehicle=True)
        self.assertEqual(response.status_code, 201)
        cache.clear()
        password = "SomeVeryStrongPassword+2026"
        activated = self.client.post(self.setup_url, {
            "token": TOKEN, "password": password,
            "confirm_password": password,
        }, format="json")
        self.assertEqual(activated.status_code, 200)
        self.client.force_authenticate(user=self.admin)
        endpoint = f"/api/drivers/admin/unified-applications/{response.data['application_id']}/decision/"
        minimal = {
            "action": "approve", "documents_reviewed": True,
            "dbs_cleared": True, "photo_disclosure_consent": True,
        }
        missing = self.client.post(endpoint, minimal, format="json")
        self.assertEqual(missing.status_code, 400)
        self.assertFalse(BaseDriver.objects.filter(user__email="newdriver@example.invalid").exists())
        with override_settings(ACT_NI_ENCRYPTION_KEY=""):
            unconfigured = self.client.post(endpoint, {
                **minimal, **self.operator_approval_fields(),
            }, format="json")
        self.assertEqual(unconfigured.status_code, 503)
        self.assertFalse(BaseDriver.objects.filter(user__email="newdriver@example.invalid").exists())
        with patch("apps.drivers.views.unified_admin.send_mail", return_value=1):
            with self.captureOnCommitCallbacks(execute=True):
                approved = self.client.post(endpoint, {
                    **minimal, **self.operator_approval_fields(),
                }, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        profile = UnifiedDriverApplication.objects.get(
            onboarding_request_id=response.data["application_id"]
        )
        self.assertTrue(profile.national_insurance_ciphertext.startswith("fernet:v1:"))
        self.assertNotIn("AB123456C", profile.national_insurance_ciphertext)
        from apps.drivers.operator_records import decrypt_operator_ni
        self.assertEqual(decrypt_operator_ni(profile.national_insurance_ciphertext), "AB123456C")
        self.assertEqual(profile.registered_keeper_name, "Synthetic Registered Keeper")
        self.assertEqual(profile.driver_available_from, date.today())
        self.assertEqual(profile.vehicle_available_from, date.today())
        details = self.client.get(
            f"/api/drivers/admin/unified-applications/{response.data['application_id']}/"
        )
        self.assertEqual(details.status_code, 200)
        self.assertTrue(details.data["operator_record"]["national_insurance_recorded"])
        self.assertNotIn("AB123456C", str(details.data))

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
                    **self.operator_approval_fields(),
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


    def approved_unified_for_lifecycle(self):
        """Use the existing synthetic onboarding path; never create a paid trip."""
        response, _ = self.apply(with_vehicle=True)
        self.assertEqual(response.status_code, 201)
        cache.clear()
        password = "SomeVeryStrongPassword+2026"
        activated = self.client.post(self.setup_url, {
            "token": TOKEN, "password": password, "confirm_password": password,
        }, format="json")
        self.assertEqual(activated.status_code, 200)
        self.client.force_authenticate(user=self.admin)
        decision = f"/api/drivers/admin/unified-applications/{response.data['application_id']}/decision/"
        with patch("apps.drivers.views.unified_admin.send_mail", return_value=1):
            with self.captureOnCommitCallbacks(execute=True):
                approved = self.client.post(decision, {
                    "action": "approve", "documents_reviewed": True,
                    "dbs_cleared": True, "photo_disclosure_consent": True,
                    **self.operator_approval_fields(),
                }, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        return response.data["application_id"]

    def new_vehicle_evidence(self):
        return {
            "vehicle_ownership": "phv_owner",
            "vehicle_class_code": "comfort",
            "vehicle_make": "Mercedes",
            "vehicle_model": "E Class",
            "vehicle_year": "2025",
            "vehicle_registration": "XY25 ABC",
            "vehicle_colour": "Silver",
            "mot_expiry": str(date.today() + timedelta(days=300)),
            "insurance_expiry": str(date.today() + timedelta(days=200)),
            "accepts_pets": "false",
            "registered_keeper_name": "Second Synthetic Keeper",
            "registered_keeper_address": "45 Synthetic Lane, London",
            "replacement_reason": "Owner approved new vehicle",
            "documents_reviewed": "true",
            "operator_records_checked": "true",
            "mot": pdf("replacement_mot.pdf"),
            "insurance": pdf("replacement_insurance.pdf"),
            "vehicle_phv": pdf("replacement_phv.pdf"),
            "v5c": pdf("replacement_v5c.pdf"),
        }

    def test_vehicle_replacement_preserves_original_vehicle_history_and_private_evidence(self):
        app_id = self.approved_unified_for_lifecycle()
        profile = UnifiedDriverApplication.objects.get(onboarding_request_id=app_id)
        original_period = OperatorVehiclePeriod.objects.get(application=profile)
        old_vehicle_id = original_period.vehicle_id
        self.assertIsNone(original_period.ceased_at)
        self.assertEqual(original_period.registered_keeper_name, "Synthetic Registered Keeper")

        endpoint = f"/api/drivers/admin/unified-applications/{app_id}/replace-vehicle/"
        changed = self.client.post(endpoint, self.new_vehicle_evidence(), format="multipart")
        self.assertEqual(changed.status_code, 200, changed.data)
        old_period = OperatorVehiclePeriod.objects.get(pk=original_period.pk)
        self.assertIsNotNone(old_period.ceased_at)
        self.assertEqual(old_period.vehicle_id, old_vehicle_id)
        self.assertEqual(old_period.registered_keeper_name, "Synthetic Registered Keeper")
        current = OperatorVehiclePeriod.objects.get(application=profile, ceased_at__isnull=True)
        self.assertNotEqual(current.vehicle_id, old_vehicle_id)
        self.assertEqual(current.vehicle_registration, "XY25 ABC")
        self.assertEqual(current.registered_keeper_name, "Second Synthetic Keeper")
        self.assertEqual(current.evidence.count(), 4)
        self.assertEqual(OperatorVehicleEvidence.objects.count(), 4)
        self.assertEqual(DriverApplicationDocument.objects.filter(application=profile).count(), 9)
        normal = NormalDriver.objects.get(driver__user__email="newdriver@example.invalid")
        self.assertEqual(normal.vehicle_id, current.vehicle_id)
        self.assertEqual(BaseDriver.objects.filter(user__email="newdriver@example.invalid").count(), 1)
        detail = self.client.get(f"/api/drivers/admin/unified-applications/{app_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["vehicle_history"]), 2)
        evidence = current.evidence.first()
        self.client.force_authenticate(user=None)
        denied = self.client.get(f"/api/drivers/admin/unified-vehicle-evidence/{evidence.pk}/")
        self.assertIn(denied.status_code, (401, 403))
        self.client.force_authenticate(user=self.admin)
        private = self.client.get(f"/api/drivers/admin/unified-vehicle-evidence/{evidence.pk}/")
        self.assertEqual(private.status_code, 200)
        self.assertEqual(private["Cache-Control"], "private, no-store")

    def test_outstanding_assignment_blocks_vehicle_swap_and_driver_cessation_without_touching_trips(self):
        app_id = self.approved_unified_for_lifecycle()
        profile = UnifiedDriverApplication.objects.get(onboarding_request_id=app_id)
        original_period = OperatorVehiclePeriod.objects.get(application=profile)
        replace_url = f"/api/drivers/admin/unified-applications/{app_id}/replace-vehicle/"
        cease_url = f"/api/drivers/admin/unified-applications/{app_id}/cease/"
        with patch("apps.drivers.views.operator_lifecycle._outstanding_assignment", return_value=True):
            swap = self.client.post(replace_url, self.new_vehicle_evidence(), format="multipart")
            stop = self.client.post(cease_url, {
                "reason": "Driver leaves ACT coverage",
                "confirmed_no_outstanding_trips": True,
            }, format="json")
        self.assertEqual(swap.status_code, 409)
        self.assertEqual(stop.status_code, 409)
        self.assertEqual(OperatorVehiclePeriod.objects.count(), 1)
        original_period.refresh_from_db()
        self.assertIsNone(original_period.ceased_at)
        self.assertTrue(User.objects.get(email="newdriver@example.invalid").is_admin_verified)

    def test_driver_cessation_closes_records_and_revokes_trip_permission(self):
        app_id = self.approved_unified_for_lifecycle()
        endpoint = f"/api/drivers/admin/unified-applications/{app_id}/cease/"
        result = self.client.post(endpoint, {
            "reason": "Driver is leaving the ACT operator",
            "confirmed_no_outstanding_trips": True,
        }, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        profile = UnifiedDriverApplication.objects.get(onboarding_request_id=app_id)
        self.assertEqual(profile.driver_ceased_available_on, date.today())
        self.assertEqual(profile.vehicle_ceased_available_on, date.today())
        period = OperatorVehiclePeriod.objects.get(application=profile)
        self.assertIsNotNone(period.ceased_at)
        driver = User.objects.get(email="newdriver@example.invalid")
        self.assertFalse(driver.is_admin_verified)
        self.assertFalse(driver.is_profile_completed)
        self.assertTrue(driver.is_active)  # Account history still accessible.
        self.assertEqual(DriverOnboardingRequest.objects.get(user=driver).status, "final_approved")
        repeat = self.client.post(endpoint, {
            "reason": "Second attempt would overwrite the audit",
            "confirmed_no_outstanding_trips": True,
        }, format="json")
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(OperatorRecordAccessAudit.objects.filter(action="availability_ceased").count(), 1)

    def test_legacy_vehicle_editor_fails_closed_only_for_approved_unified_driver(self):
        app_id = self.approved_unified_for_lifecycle()
        normal = NormalDriver.objects.get(driver__user__email="newdriver@example.invalid")
        endpoint = f"/api/admin-panel/drivers/{normal.pk}/update/"
        original = normal.vehicle.make
        result = self.client.patch(endpoint, {"vehicle_make": "Unreviewed swap"}, format="multipart")
        self.assertEqual(result.status_code, 409, getattr(result, "data", None))
        normal.refresh_from_db()
        self.assertEqual(normal.vehicle.make, original)
        self.assertTrue(OperatorVehiclePeriod.objects.filter(
            application__onboarding_request_id=app_id, ceased_at__isnull=True,
        ).exists())

    def test_superuser_ni_inspection_requires_reason_and_is_audited(self):
        app_id = self.approved_unified_for_lifecycle()
        endpoint = f"/api/drivers/admin/unified-applications/{app_id}/ni-inspection/"
        missing = self.client.post(endpoint, {}, format="json")
        self.assertEqual(missing.status_code, 400)
        staff = User.objects.create_user(
            username="staff", email="staff@example.invalid",
            password="synthetic-admin-password", account_type="normal",
        )
        staff.is_staff = True
        staff.save()
        self.client.force_authenticate(user=staff)
        denied = self.client.post(endpoint, {"reason": "TfL regulatory inspection"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(user=self.admin)
        readback = self.client.post(endpoint, {"reason": "TfL regulatory inspection"}, format="json")
        self.assertEqual(readback.status_code, 200)
        self.assertEqual(readback.data["national_insurance_number"], "AB123456C")
        self.assertEqual(readback["Cache-Control"], "private, no-store")
        audits = OperatorRecordAccessAudit.objects.filter(action="ni_inspection")
        self.assertEqual(audits.count(), 1)
        self.assertEqual(audits.first().actor_id, self.admin.pk)
        self.assertNotIn("AB123456C", audits.first().reason)
