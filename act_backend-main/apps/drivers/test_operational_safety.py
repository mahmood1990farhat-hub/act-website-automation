"""Finite safety integration tests. Synthetic DB rows, no payment/email calls."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
from queue import Queue
import time as clock
from types import SimpleNamespace
from unittest import skipUnless

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.drivers.models import (
    BaseDriver, NormalDriver, DriverOnboardingRequest, UnifiedDriverApplication,
    OperatorVehiclePeriod, OperatorRecordAccessAudit,
)
from apps.drivers.operational_safety import (
    DriverLifecycleConflict, lock_driver_record, handle_unified_account_action,
)
from apps.vehicle.models import Vehicle, VehicleType
from apps.trips.models import Trip

KEY = "BwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwc="


def fixture(test):
    User = get_user_model()
    test.admin = User.objects.create_user(
        username="operator", email="operator-safety@example.invalid", password="synthetic-only",
        is_staff=True, is_superuser=True, first_name="Test", last_name="Operator", address="Test",
    )
    test.user = User.objects.create_user(
        username="driver", email="driver-safety@example.invalid", password="synthetic-only",
        first_name="Synthetic", last_name="Driver", address="Example street",
        phone_number="+447700900987", account_type="normal_driver",
        is_active=True, is_profile_completed=True, is_admin_verified=True,
    )
    test.kind = VehicleType.objects.create(
        code="comfort", name_en="Comfort", name_ar="Comfort", icon="synthetic.png", max_passengers_count=4,
    )
    test.vehicle = Vehicle.objects.create(
        vehicle_number="AB25 TST", make="Test", model="Car", color="Black",
        year_of_manufacture=2025, vehicle_type=test.kind, mot="", phv="",
    )
    test.driver = BaseDriver.objects.create(
        user=test.user, pco="", dbs="", dvla="", pco_licence_number="TEST-PCO", driver_photo="synthetic.png",
    )
    test.normal = NormalDriver.objects.create(driver=test.driver, vehicle=test.vehicle)
    test.onboarding = DriverOnboardingRequest.objects.create(
        user=test.user, full_name="Synthetic Driver", mobile_number=test.user.phone_number,
        email_address=test.user.email, home_postcode="SW1A 1AA", preferred_communication="email",
        years_experience="5_plus", vehicle_ownership="phv_owner", vehicle_type="5_seater_standard",
        fuel_type="ev", availability="full_time", notification_method="email", status="final_approved",
    )
    from apps.drivers.operator_records import encrypt_operator_ni
    test.profile = UnifiedDriverApplication.objects.create(
        onboarding_request=test.onboarding, date_of_birth=date(1990, 1, 1), address="Example street",
        postcode="SW1A 1AA", pco_badge_number="TEST-PCO", pco_badge_expiry=date.today()+timedelta(days=200),
        password_set_at=timezone.now(), passenger_photo_disclosure_consent=True,
        driver_available_from=date.today(), vehicle_available_from=date.today(), vehicle_class_code="comfort",
        national_insurance_ciphertext=encrypt_operator_ni("AB123456C"),
        registered_keeper_name="Synthetic Keeper", registered_keeper_address="Example street",
    )
    test.period = OperatorVehiclePeriod.objects.create(
        application=test.profile, vehicle=test.vehicle, vehicle_registration=test.vehicle.vehicle_number,
        vehicle_make="Test", vehicle_model="Car", vehicle_colour="Black", vehicle_class_code="comfort",
        vehicle_year=2025, ownership="phv_owner", registered_keeper_name="Synthetic Keeper",
        registered_keeper_address="Example street", available_from=timezone.now(), reviewed_by=test.admin,
    )
    test.client = APIClient()
    test.client.force_authenticate(user=test.admin)


def trip_values(driver_id, kind_id):
    return dict(
        pickup_lat=51.5, pickup_lng=-0.1, dropoff_lat=51.6, dropoff_lng=-0.2,
        trip_date=date.today()+timedelta(days=1), trip_time=time(12), cost="40.00",
        passengers_count=1, base_driver_id=driver_id, car_type_id=kind_id, status="pending",
    )


@override_settings(ACT_NI_ENCRYPTION_KEY=KEY)
class OperationalSafetyTests(TestCase):
    def setUp(self):
        fixture(self)

    def account_url(self, action):
        return f"/api/admin-panel/users/{self.user.pk}/{action}/"

    def test_old_deactivate_route_blocks_assigned_journey(self):
        trip = Trip.objects.create(**trip_values(self.driver.pk, self.kind.pk))
        result = self.client.post(self.account_url("deactivate"), {}, format="json")
        self.assertEqual(result.status_code, 409, result.data)
        self.user.refresh_from_db()
        trip.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(trip.base_driver_id, self.driver.pk)
        self.assertEqual(trip.status, "pending")
        self.assertFalse(OperatorRecordAccessAudit.objects.exists())

    def test_suspend_restore_is_audited_without_false_cessation(self):
        self.assertEqual(self.client.post(self.account_url("deactivate"), {}).status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNone(self.profile.driver_ceased_available_on)
        self.assertEqual(self.client.post(self.account_url("activate"), {}).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(set(OperatorRecordAccessAudit.objects.values_list("action", flat=True)),
                         {"account_suspended", "account_restored"})

    def test_ceased_driver_cannot_be_revived_by_old_account_button(self):
        result = self.client.post(f"/api/drivers/admin/unified-applications/{self.onboarding.pk}/cease/", {
            "reason": "Driver no longer works with ACT", "confirmed_no_outstanding_trips": True,
        }, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.client.post(self.account_url("activate"), {}).status_code, 409)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_admin_verified)

    def test_suspended_driver_can_be_permanently_ceased_without_reactivation(self):
        self.assertEqual(self.client.post(self.account_url("deactivate"), {}).status_code, 200)
        result = self.client.post(f"/api/drivers/admin/unified-applications/{self.onboarding.pk}/cease/", {
            "reason": "Permanent exit following suspension", "confirmed_no_outstanding_trips": True,
        }, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.profile.driver_ceased_available_on)
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.is_admin_verified)

    def test_stale_assignment_cannot_bypass_suspension(self):
        stale_trip = Trip(**trip_values(self.driver.pk, self.kind.pk))
        self.client.post(self.account_url("deactivate"), {})
        with self.assertRaises(DriverLifecycleConflict):
            stale_trip.save()
        self.assertEqual(Trip.objects.count(), 0)

    def test_completion_and_confirmation_only_saves_still_work(self):
        trip = Trip.objects.create(**trip_values(self.driver.pk, self.kind.pk))
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        trip.passenger_confirmation_sent_at = timezone.now()
        trip.save(update_fields=["passenger_confirmation_sent_at"])
        trip.status = "completed"
        trip.save(update_fields=["status"])
        trip.refresh_from_db()
        self.assertEqual(trip.status, "completed")

    def test_historical_vehicle_edits_blocked_but_legacy_vehicles_unchanged(self):
        self.vehicle.make = "Unreviewed"
        with self.assertRaises(DriverLifecycleConflict):
            self.vehicle.save(update_fields=["make"])
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.make, "Test")
        legacy = Vehicle.objects.create(vehicle_number="ZZ25 TST", year_of_manufacture=2025,
                                        vehicle_type=self.kind, mot="", phv="")
        legacy.make = "Permitted legacy correction"
        legacy.save(update_fields=["make"])
        legacy.refresh_from_db()
        self.assertEqual(legacy.make, "Permitted legacy correction")

    def test_legacy_passenger_account_action_preserved(self):
        passenger = get_user_model().objects.create_user(
            username="passenger", email="passenger-safety@example.invalid", password="synthetic",
            first_name="Example", last_name="Passenger", address="Example", account_type="passenger",
        )
        result = self.client.post(f"/api/admin-panel/users/{passenger.pk}/deactivate/", {})
        self.assertEqual(result.status_code, 200, result.data)
        passenger.refresh_from_db()
        self.assertFalse(passenger.is_active)

    def test_private_ni_request_is_not_duplicated_in_profiler_storage(self):
        from silk.models import Request
        path = f"/api/drivers/admin/unified-applications/{self.onboarding.pk}/ni-inspection/"
        before = Request.objects.filter(path=path).count()
        response = self.client.post(path, {"reason": "Authorised synthetic compliance inspection"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["national_insurance_number"], "AB123456C")
        self.assertEqual(Request.objects.filter(path=path).count(), before)
        self.assertFalse(settings.SILKY_INTERCEPT_FUNC(SimpleNamespace(path_info=path)))


@override_settings(ACT_NI_ENCRYPTION_KEY=KEY)
@skipUnless(connection.vendor == "postgresql", "PostgreSQL row-lock verification")
class OperationalConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixture(self)

    def wait_until_locked(self, pid):
        deadline = clock.monotonic() + 8
        while clock.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=%s AND NOT granted)", [pid])
                if cursor.fetchone()[0]:
                    return
            clock.sleep(0.05)
        self.fail("Competing assignment did not wait on the shared driver lock")

    def test_waiting_assignment_reloads_committed_suspension(self):
        ready = Queue()
        driver_id, kind_id = self.driver.pk, self.kind.pk
        def worker():
            connections.close_all()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '12s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    ready.put(cursor.fetchone()[0])
                try:
                    Trip.objects.create(**trip_values(driver_id, kind_id))
                    return "unexpected_assignment"
                except DriverLifecycleConflict:
                    return "blocked"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                driver, _ = lock_driver_record(driver_id)
                future = pool.submit(worker)
                self.wait_until_locked(ready.get(timeout=5))
                driver.user.is_active = False
                driver.user.save(update_fields=["is_active"])
            self.assertEqual(future.result(timeout=15), "blocked")
        self.assertEqual(Trip.objects.count(), 0)

    def test_waiting_suspension_reloads_committed_assignment(self):
        ready = Queue()
        user_id, driver_id, kind_id, actor_id = self.user.pk, self.driver.pk, self.kind.pk, self.admin.pk
        def worker():
            connections.close_all()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '12s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    ready.put(cursor.fetchone()[0])
                actor = get_user_model().objects.get(pk=actor_id)
                try:
                    handle_unified_account_action(user_id, "deactivate", actor)
                    return "unexpected_suspension"
                except DriverLifecycleConflict:
                    return "blocked"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                lock_driver_record(driver_id)
                Trip.objects.create(**trip_values(driver_id, kind_id))
                future = pool.submit(worker)
                self.wait_until_locked(ready.get(timeout=5))
            self.assertEqual(future.result(timeout=15), "blocked")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(Trip.objects.count(), 1)
