"""Focused admin-detail regression tests; synthetic records, no journey writes.

Reuse the accepted operator-safety fixture rather than recreate onboarding.
The original booking/payment, lifecycle and frontend suites are not repeated.
"""
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.drivers.test_operational_safety import KEY, fixture


@override_settings(ACT_NI_ENCRYPTION_KEY=KEY)
class AdminDetailResponseTests(TestCase):
    def setUp(self):
        fixture(self)
        self.url = f"/api/drivers/admin/unified-applications/{self.onboarding.pk}/"

    def get_detail(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        return response

    def assert_not_cacheable(self, response):
        directives = {item.strip() for item in response.get("Cache-Control", "").split(",")}
        self.assertTrue({"private", "no-store", "no-cache", "max-age=0", "must-revalidate"}.issubset(directives))
        self.assertTrue(response.has_header("Expires"))

    def test_active_verified_driver_remains_available(self):
        response = self.get_detail()
        self.assertIs(response.data["operator_record"]["is_currently_available"], True)
        self.assertNotIn("national_insurance_number", response.data["operator_record"])
        self.assertNotIn("AB123456C", str(response.data))

    def test_suspended_driver_is_unavailable_without_changing_history(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.get_detail()
        self.assertIs(response.data["operator_record"]["is_currently_available"], False)
        self.profile.refresh_from_db()
        self.period.refresh_from_db()
        self.user.refresh_from_db()
        self.assertIsNone(self.profile.driver_ceased_available_on)
        self.assertIsNone(self.period.ceased_at)
        self.assertTrue(self.user.is_admin_verified)
        self.assertTrue(self.user.is_profile_completed)

    def test_next_response_reflects_restored_account(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertIs(self.get_detail().data["operator_record"]["is_currently_available"], False)
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        restored = self.get_detail()
        self.assertIs(restored.data["operator_record"]["is_currently_available"], True)
        self.assert_not_cacheable(restored)

    def test_permanently_ceased_driver_remains_unavailable(self):
        self.profile.driver_ceased_available_on = timezone.localdate()
        self.profile.save(update_fields=["driver_ceased_available_on"])
        self.assertIs(self.get_detail().data["operator_record"]["is_currently_available"], False)

    def test_driver_without_availability_start_remains_unavailable(self):
        self.profile.driver_available_from = None
        self.profile.save(update_fields=["driver_available_from"])
        self.assertIs(self.get_detail().data["operator_record"]["is_currently_available"], False)

    def test_existing_verification_and_completion_requirements_are_preserved(self):
        for field in ("is_admin_verified", "is_profile_completed"):
            with self.subTest(field=field):
                setattr(self.user, field, False)
                self.user.save(update_fields=[field])
                self.assertIs(self.get_detail().data["operator_record"]["is_currently_available"], False)
                setattr(self.user, field, True)
                self.user.save(update_fields=[field])

    def test_success_response_has_private_no_store_headers(self):
        self.assert_not_cacheable(self.get_detail())

    def test_anonymous_access_is_still_denied_and_not_cached(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (401, 403))
        self.assert_not_cacheable(response)
        self.assertNotIn("operator_record", response.data)

    def test_non_admin_access_is_still_denied_and_not_cached(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assert_not_cacheable(response)
        self.assertNotIn("operator_record", response.data)

    def test_missing_application_response_is_not_cached(self):
        response = self.client.get(f"/api/drivers/admin/unified-applications/{self.onboarding.pk + 1000000}/")
        self.assertEqual(response.status_code, 404)
        self.assert_not_cacheable(response)
