"""Real-model/JWT report and transition tests with synthetic local data only.

Use myProject.settings.journey_report_tests in the existing isolated PostGIS
test environment. Notification and tracking publication are replaced; no
payment, provider, device, email or live journey is accessed.
"""

from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.drivers.models import BaseDriver
from apps.earnings.models import CompanyRevenueLedger, DriverEarningLedger
from apps.passengers.models import Passenger
from apps.trips.models import Trip
from apps.trips.serializers.trip import TripSerializer
from apps.vehicle.models import VehicleType


class JourneyReportTests(TestCase):
    def setUp(self):
        self.start_notification = self.replace("apps.trips.views.start_trip.notify_user")
        self.end_notification = self.replace("apps.trips.views.end_trip.notify_user")
        self.stop_tracking = self.replace("apps.trips.views.end_trip.stop_trip_tracking")
        self.driver_user = self.user("report-driver", "normal_driver")
        self.other_driver_user = self.user("other-report-driver", "normal_driver")
        self.driver = BaseDriver.objects.create(user=self.driver_user)
        self.other_driver = BaseDriver.objects.create(user=self.other_driver_user)
        self.car_type = VehicleType.objects.create(
            code="report-comfort", name_en="Comfort Class", name_ar="فئة الراحة",
            icon="vehicle_types/icons/synthetic.png", max_passengers_count=4,
        )
        self.trip = Trip.objects.create(
            pickup_lat=51.47, pickup_lng=-0.45,
            dropoff_lat=51.50, dropoff_lng=-0.12,
            pickup_str="Synthetic airport pickup", dropoff_str="Synthetic city drop-off",
            trip_date=date(2026, 11, 23), trip_time=time(12, 0),
            car_type=self.car_type, cost=Decimal("80.00"), passengers_count=2,
            base_driver=self.driver, status="driver_on_the_way", is_paid=True,
            is_guest_checkout=True, passenger_name="Synthetic Passenger",
            passenger_email="journey-report@example.invalid",
            expected_trip_duration_minutes=90, distance_miles=15.5,
        )
        self.client = self.client_for(self.driver_user)
        self.detail_url = f"/api/driver/trips/{self.trip.pk}/"
        self.start_url = f"/api/trips/{self.trip.pk}/start/"
        self.complete_url = f"/api/trips/{self.trip.pk}/complete/"
        self.started = timezone.now().replace(microsecond=0) - timedelta(minutes=5)
        self.completed = self.started + timedelta(minutes=3)

    def replace(self, target):
        replacement = patch(target)
        value = replacement.start()
        self.addCleanup(replacement.stop)
        return value

    def user(self, name, account_type):
        return get_user_model().objects.create_user(
            username=name, email=f"{name}@example.invalid", password="synthetic-report-password",
            first_name="Synthetic", last_name=name, address="Synthetic",
            account_type=account_type, is_active=True,
            is_admin_verified=True, is_profile_completed=True,
        )

    def client_for(self, user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        return client

    def set_trip(self, **changes):
        # Test fixture setup only; production transitions continue through save.
        Trip.objects.filter(pk=self.trip.pk).update(**changes)
        self.trip.refresh_from_db()

    def add_earning(self, driver=None):
        return DriverEarningLedger.objects.create(
            trip=self.trip, driver=driver or self.driver,
            gross_amount=Decimal("80.00"), commission_amount=Decimal("16.00"),
            net_amount=Decimal("64.00"), currency="GBP", status="AVAILABLE",
        )

    def get_report(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200, response.data)
        return response, response.data["data"]["journey_report"]

    def test_first_start_records_server_time_and_ignores_client_timestamp(self):
        with patch("apps.trips.views.start_trip.timezone.now", return_value=self.started):
            response = self.client.post(self.start_url, {
                "started_at": "2000-01-01T00:00:00Z",
                "completed_at": "2000-01-02T00:00:00Z",
            }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "active")
        self.assertEqual(self.trip.started_at, self.started)
        self.assertTrue(timezone.is_aware(self.trip.started_at))
        self.assertIsNone(self.trip.completed_at)

    def test_duplicate_start_preserves_first_time_and_does_not_notify_twice(self):
        passenger = Passenger.objects.create(user=self.user("report-passenger", "passenger"))
        self.set_trip(passenger=passenger)
        with patch("apps.trips.views.start_trip.timezone.now", return_value=self.started):
            first = self.client.post(self.start_url, {}, format="json")
        with patch("apps.trips.views.start_trip.timezone.now", return_value=self.completed):
            second = self.client.post(self.start_url, {}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.started_at, self.started)
        self.start_notification.assert_called_once()

    def test_legacy_active_retry_does_not_invent_start_time(self):
        self.set_trip(status="active", started_at=None)
        response = self.client.post(self.start_url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.started_at)
        self.start_notification.assert_not_called()

    def test_unpaid_or_invalid_start_state_does_not_record_time(self):
        for changes in ({"is_paid": False}, {"is_paid": True, "status": "accepted"}):
            with self.subTest(changes=changes):
                self.set_trip(**changes)
                response = self.client.post(self.start_url, {}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.trip.refresh_from_db()
                self.assertIsNone(self.trip.started_at)
        self.start_notification.assert_not_called()

    def test_completion_records_time_once_with_single_financial_records(self):
        self.set_trip(status="active", started_at=self.started)
        with patch("apps.trips.views.end_trip.timezone.now", return_value=self.completed):
            first = self.client.post(self.complete_url, {
                "completed_at": "2000-01-01T00:00:00Z",
            }, format="json")
        with patch("apps.trips.views.end_trip.timezone.now", return_value=self.completed + timedelta(hours=1)):
            second = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "completed")
        self.assertEqual(self.trip.started_at, self.started)
        self.assertEqual(self.trip.completed_at, self.completed)
        self.assertEqual(DriverEarningLedger.objects.filter(trip=self.trip).count(), 1)
        self.assertEqual(CompanyRevenueLedger.objects.filter(trip=self.trip).count(), 1)
        self.stop_tracking.assert_called_once_with(self.trip.pk, reason="completed")

    def test_financial_failure_rolls_back_completion_time_status_and_new_ledger(self):
        self.set_trip(status="active", started_at=self.started)

        def partially_write_then_fail(trip):
            DriverEarningLedger.objects.create(
                trip=trip, driver=self.driver, gross_amount="80.00",
                commission_amount="16.00", net_amount="64.00", currency="GBP",
            )
            raise RuntimeError("Synthetic ledger failure")

        with patch(
            "apps.earnings.services.earnings_calculator.EarningsCalculator.calculate_and_record_earnings",
            side_effect=partially_write_then_fail,
        ):
            response = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(response.status_code, 500, response.data)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "active")
        self.assertEqual(self.trip.started_at, self.started)
        self.assertIsNone(self.trip.completed_at)
        self.assertFalse(DriverEarningLedger.objects.filter(trip=self.trip).exists())
        self.assertFalse(CompanyRevenueLedger.objects.filter(trip=self.trip).exists())
        self.stop_tracking.assert_not_called()
        self.end_notification.assert_not_called()

    def test_legacy_completed_ledger_repair_does_not_invent_actual_times(self):
        self.set_trip(status="completed", started_at=None, completed_at=None)
        response = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.started_at)
        self.assertIsNone(self.trip.completed_at)
        self.assertEqual(DriverEarningLedger.objects.filter(trip=self.trip).count(), 1)
        self.assertEqual(CompanyRevenueLedger.objects.filter(trip=self.trip).count(), 1)

    def test_assigned_driver_gets_completed_report_with_actual_utc_times(self):
        self.set_trip(status="completed", started_at=self.started, completed_at=self.completed)
        self.add_earning()
        response, report = self.get_report()
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response.data["data"]["id"], self.trip.pk)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["reference"], str(self.trip.pk))
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["timing_status"], "recorded")
        self.assertEqual(parse_datetime(report["started_at"]), self.started)
        self.assertEqual(parse_datetime(report["completed_at"]), self.completed)
        self.assertTrue(report["started_at"].endswith("Z"))
        self.assertTrue(report["completed_at"].endswith("Z"))
        self.assertEqual(report["actual_duration_seconds"], 180)
        self.assertEqual(report["scheduled_pickup"], {"date": "2026-11-23", "time": "12:00:00"})
        self.assertEqual(report["pickup_address"], "Synthetic airport pickup")
        self.assertEqual(report["dropoff_address"], "Synthetic city drop-off")
        self.assertEqual(report["vehicle_class"]["name_en"], "Comfort Class")
        self.assertEqual(report["booked_fare"], {"amount": "80.00", "currency": "GBP"})

    def test_report_uses_persisted_driver_net_not_current_commission_estimate(self):
        self.set_trip(status="completed")
        ledger = self.add_earning()
        self.driver.driver_commission_percentage = Decimal("50.00")
        self.driver.save(update_fields=["driver_commission_percentage"])
        _, report = self.get_report()
        self.assertEqual(report["driver_earnings"], {
            "amount": "64.00", "currency": "GBP", "status": "AVAILABLE",
            "recorded_at": ledger.created_at.isoformat().replace("+00:00", "Z"),
        })

    def test_legacy_report_does_not_substitute_booking_estimate_or_ledger_time(self):
        self.set_trip(status="completed", started_at=None, completed_at=None)
        self.add_earning()
        _, report = self.get_report()
        self.assertIsNone(report["started_at"])
        self.assertIsNone(report["completed_at"])
        self.assertIsNone(report["actual_duration_seconds"])
        self.assertEqual(report["timing_status"], "not_recorded")
        self.assertIsNotNone(report["driver_earnings"]["recorded_at"])

    def test_report_read_does_not_create_or_repair_missing_earnings(self):
        self.set_trip(status="completed")
        with CaptureQueriesContext(connection) as queries:
            _, report = self.get_report()
        self.assertIsNone(report["driver_earnings"])
        writes = [q["sql"] for q in queries.captured_queries
                  if q["sql"].lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}]
        self.assertEqual(writes, [])
        self.assertFalse(DriverEarningLedger.objects.filter(trip=self.trip).exists())
        self.assertFalse(CompanyRevenueLedger.objects.filter(trip=self.trip).exists())

    def test_report_does_not_reveal_a_previous_drivers_earning(self):
        self.set_trip(status="completed")
        self.add_earning(driver=self.other_driver)
        _, report = self.get_report()
        self.assertIsNone(report["driver_earnings"])

    def test_report_is_absent_until_completed(self):
        for state in ("accepted", "driver_on_the_way", "active", "cancelled"):
            with self.subTest(state=state):
                self.set_trip(status=state)
                _, report = self.get_report()
                self.assertIsNone(report)

    def test_partial_or_inverted_times_never_produce_an_estimated_duration(self):
        for started, completed, expected in (
            (self.started, None, "partial"),
            (None, self.completed, "partial"),
            (self.completed, self.started, "invalid_order"),
        ):
            with self.subTest(expected=expected, started=started):
                self.set_trip(status="completed", started_at=started, completed_at=completed)
                _, report = self.get_report()
                self.assertEqual(report["timing_status"], expected)
                self.assertIsNone(report["actual_duration_seconds"])

    def test_zero_duration_is_recorded_and_midnight_duration_is_exact(self):
        midnight = datetime(2026, 11, 23, 0, 0, tzinfo=datetime_timezone.utc)
        for started, completed, seconds in (
            (midnight, midnight, 0),
            (midnight - timedelta(minutes=2), midnight + timedelta(minutes=3), 300),
        ):
            with self.subTest(seconds=seconds):
                self.set_trip(status="completed", started_at=started, completed_at=completed)
                _, report = self.get_report()
                self.assertEqual(report["timing_status"], "recorded")
                self.assertEqual(report["actual_duration_seconds"], seconds)

    def test_other_driver_cannot_read_report_or_mutate_actual_times(self):
        client = self.client_for(self.other_driver_user)
        self.assertEqual(client.get(self.detail_url).status_code, 404)
        self.assertEqual(client.post(self.start_url, {}, format="json").status_code, 404)
        self.set_trip(status="active")
        self.assertEqual(client.post(self.complete_url, {}, format="json").status_code, 404)
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.started_at)
        self.assertIsNone(self.trip.completed_at)

    def test_anonymous_passenger_and_unapproved_accounts_cannot_read_report(self):
        self.assertEqual(APIClient().get(self.detail_url).status_code, 401)
        passenger = self.user("non-driver-report-reader", "passenger")
        Passenger.objects.create(user=passenger)
        self.assertEqual(self.client_for(passenger).get(self.detail_url).status_code, 403)
        self.driver_user.is_admin_verified = False
        self.driver_user.save(update_fields=["is_admin_verified"])
        self.assertEqual(self.client.get(self.detail_url).status_code, 403)

    def test_model_serializer_does_not_accept_actual_times_as_client_fields(self):
        serializer = TripSerializer(self.trip, data={
            "started_at": "2000-01-01T00:00:00Z",
            "completed_at": "2000-01-01T01:00:00Z",
        }, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {})
