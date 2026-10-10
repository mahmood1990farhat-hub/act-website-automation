"""Isolated acceptance/commission/ledger regressions. No live provider writes."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.drivers.models import BaseDriver
from apps.earnings.models import CommissionRule, DriverCommissionGroup, DriverCommissionMembership, DriverPayoutAgreement, DriverEarningLedger, CompanyRevenueLedger
from apps.earnings.services.commission_lock import lock_commission_configuration
from apps.earnings.services.earnings_calculator import EarningsCalculator
from apps.earnings.services.payout_agreements import split_driver_payout
from apps.trips.models import Trip
from apps.trips.serializers.trip import TripWithStopPointBasicSerializer
from apps.trips.tests import test_driver_assignment_lifecycle as fixtures

URL = '/api/admin-panel/commission-management/'


class PayoutFixtures:
    _driver = fixtures.DriverAssignmentLifecycleTests._driver

    def setUp(self):
        fixtures.DriverAssignmentLifecycleTests.setUp(self)
        self.trip.cost = Decimal('100.00')
        self.trip.save(update_fields=['cost'])
        for name in (
            'apps.trips.views.accept_trip.send_trip_accepted_to_passenger',
            'apps.trips.views.accept_trip.send_trip_accepted_to_admin',
            'apps.trips.views.accept_trip.ensure_booking_confirmation_pdf',
            'apps.trips.views.driver_cancel_trip.send_driver_cancellation_to_admin',
            'apps.trips.views.driver_cancel_trip.send_driver_cancellation_to_passenger',
            'apps.trips.views.driver_cancel_trip.stop_trip_tracking',
            'apps.trips.views.end_trip.stop_trip_tracking',
        ):
            mocked = patch(name)
            mocked.start()
            self.addCleanup(mocked.stop)

    def client_for(self, driver):
        client = APIClient()
        client.force_authenticate(user=driver.user)
        return client

    def accept(self, driver):
        response = self.client_for(driver).post(f'/api/trips/{self.trip.pk}/accept/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        return response

    def change(self, action, **values):
        current = self.admin_client.get(URL)
        self.assertEqual(current.status_code, 200, current.data)
        return self.admin_client.post(URL, {
            'action': action, 'revision': current.data['data']['revision'],
            'reason': 'Isolated payout regression', **values,
        }, format='json')

    def group_for(self, driver, rate='15.00'):
        group = DriverCommissionGroup.objects.create(name='Payout test group', company_percentage=Decimal(rate))
        DriverCommissionMembership.objects.create(driver=driver, group=group)
        return group

    def complete(self, driver):
        client = self.client_for(driver)
        for suffix in ('driver-on-the-way', 'start', 'complete'):
            response = client.post(f'/api/trips/{self.trip.pk}/{suffix}/', {}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        self.trip.refresh_from_db()
        return DriverEarningLedger.objects.get(trip=self.trip)


@override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
class PayoutAgreementTests(PayoutFixtures, TestCase):
    def test_group_edit_preserves_accepted_display_and_completed_ledger(self):
        group = self.group_for(self.driver1)
        response = self.accept(self.driver1)
        self.assertEqual(response.data['data']['driver_earnings'], '85.00')
        self.assertNotIn('cost', response.data['data'])
        self.assertNotIn('company_percentage', response.data['data'])
        saved = self.change('set_group_rate', group_id=group.pk, company_percentage='30.00')
        self.assertEqual(saved.status_code, 200, saved.data)
        display = TripWithStopPointBasicSerializer(self.trip, context={'for_driver': True, 'base_driver': self.driver1}).data
        self.assertEqual(display['driver_earnings'], '85.00')
        self.assertNotIn('payout_agreements', display)
        for private_field in TripWithStopPointBasicSerializer.DRIVER_PRIVATE_FIELDS:
            self.assertNotIn(private_field, display)
        self.assertEqual(display['driver_earnings'], '85.00')
        earning = self.complete(self.driver1)
        self.assertEqual(earning.net_amount, Decimal('85.00'))
        self.assertEqual(earning.commission_amount, Decimal('15.00'))
        self.assertEqual(CompanyRevenueLedger.objects.get(trip=self.trip).amount, Decimal('15.00'))
        again = self.client_for(self.driver1).post(f'/api/trips/{self.trip.pk}/complete/', {}, format='json')
        self.assertEqual(again.status_code, 200, again.data)
        self.assertEqual(DriverEarningLedger.objects.filter(trip=self.trip).count(), 1)
        self.assertEqual(DriverPayoutAgreement.objects.filter(trip=self.trip).count(), 1)

    def test_global_edit_preserves_existing_accepted_fallback(self):
        self.accept(self.driver1)
        result = self.change('set_global', company_percentage='40.00')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.complete(self.driver1).net_amount, Decimal('80.00'))

    def test_individual_share_and_return_to_global_preserve_agreement(self):
        self.driver1.driver_commission_percentage = Decimal('75.00')
        self.driver1.save()
        self.accept(self.driver1)
        result = self.change('clear_individual', driver_ids=[self.driver1.pk])
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.complete(self.driver1).net_amount, Decimal('75.00'))

    def test_group_release_does_not_reprice_accepted_journey(self):
        group = self.group_for(self.driver1)
        self.accept(self.driver1)
        result = self.change('release_members', group_id=group.pk, driver_ids=[self.driver1.pk])
        self.assertEqual(result.status_code, 200, result.data)
        self.assertFalse(DriverCommissionMembership.objects.filter(driver=self.driver1).exists())
        self.assertEqual(self.complete(self.driver1).net_amount, Decimal('85.00'))

    def test_driver_cancellation_preserves_history_and_reacceptance_creates_new_terms(self):
        self.group_for(self.driver1)
        self.accept(self.driver1)
        original = DriverPayoutAgreement.objects.get(trip=self.trip)
        cancelled = self.client_for(self.driver1).post(f'/api/trips/{self.trip.pk}/driver-cancel/', {'cancellation_reason': 'Test release'}, format='json')
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        original.refresh_from_db()
        self.assertIsNotNone(original.released_at)
        self.assertEqual(original.net_amount, Decimal('85.00'))
        self.accept(self.driver2)
        replacement = DriverPayoutAgreement.objects.get(trip=self.trip, released_at__isnull=True)
        self.assertNotEqual(replacement.pk, original.pk)
        self.assertEqual(replacement.driver_id, self.driver2.pk)
        self.assertEqual(replacement.net_amount, Decimal('80.00'))
        self.assertEqual(self.complete(self.driver2).net_amount, Decimal('80.00'))
        self.assertEqual(DriverPayoutAgreement.objects.filter(trip=self.trip).count(), 2)
        self.assertFalse(DriverEarningLedger.objects.filter(driver=self.driver1, trip=self.trip).exists())

    def test_duplicate_acceptance_does_not_create_second_agreement(self):
        self.accept(self.driver1)
        again = self.client_for(self.driver1).post(f'/api/trips/{self.trip.pk}/accept/', {}, format='json')
        self.assertEqual(again.status_code, 400)
        self.assertEqual(DriverPayoutAgreement.objects.filter(trip=self.trip).count(), 1)

    def test_historical_unsnapshotted_assignment_is_not_backfilled_or_repriced_by_admin(self):
        self.trip.base_driver = self.driver1
        self.trip.status = 'accepted'
        self.trip.save(update_fields=['base_driver', 'status'])
        refused = self.change('set_individual', driver_ids=[self.driver1.pk], company_percentage='50.00')
        self.assertEqual(refused.status_code, 409, refused.data)
        self.assertFalse(DriverPayoutAgreement.objects.filter(trip=self.trip).exists())
        self.driver1.refresh_from_db()
        self.assertIsNone(self.driver1.driver_commission_percentage)

    def test_mismatching_fare_cannot_silently_reprice_completion(self):
        self.accept(self.driver1)
        self.trip.cost = Decimal('101.00')
        self.trip.status = 'completed'
        self.trip.save(update_fields=['cost', 'status'])
        with self.assertRaises(ValueError):
            EarningsCalculator.calculate_and_record_earnings(self.trip)
        self.assertFalse(DriverEarningLedger.objects.filter(trip=self.trip).exists())

    def test_agreement_terms_cannot_be_edited_or_deleted(self):
        self.accept(self.driver1)
        agreement = DriverPayoutAgreement.objects.get(trip=self.trip)
        agreement.net_amount = Decimal('1.00')
        with self.assertRaises(ValidationError):
            agreement.save()
        with self.assertRaises(ValidationError):
            DriverPayoutAgreement.objects.filter(pk=agreement.pk).update(net_amount=Decimal('1.00'))
        with self.assertRaises(ValidationError):
            agreement.delete()
        agreement.refresh_from_db()
        self.assertEqual(agreement.net_amount, Decimal('80.00'))

    def test_stale_driver_object_cannot_bypass_membership_exclusivity(self):
        stale = BaseDriver.objects.get(pk=self.driver1.pk)
        self.driver1.driver_commission_percentage = Decimal('75.00')
        self.driver1.save()
        group = DriverCommissionGroup.objects.create(name='Stale test', company_percentage=Decimal('10.00'))
        with self.assertRaises(ValidationError):
            DriverCommissionMembership.objects.create(driver=stale, group=group)

    def test_legacy_vehicle_rate_is_captured_without_changing_precedence(self):
        rule = CommissionRule.objects.create(vehicle_type=self.comfort, company_percentage=Decimal('25.00'), driver_percentage=Decimal('75.00'))
        CommissionRule.objects.create(company_percentage=Decimal('10.00'), driver_percentage=Decimal('90.00'))
        self.accept(self.driver1)
        rule.company_percentage = Decimal('40.00')
        rule.driver_percentage = Decimal('60.00')
        rule.save()
        self.assertEqual(self.complete(self.driver1).net_amount, Decimal('75.00'))

    def test_failed_acceptance_rolls_back_agreement_with_trip(self):
        with patch('apps.trips.models.Trip.save', side_effect=RuntimeError('Isolated write failure')):
            response = self.client_for(self.driver1).post(f'/api/trips/{self.trip.pk}/accept/', {}, format='json')
        self.assertEqual(response.status_code, 500)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, 'pending')
        self.assertFalse(DriverPayoutAgreement.objects.filter(trip=self.trip).exists())


class PayoutRoundingTests(SimpleTestCase):
    def test_penny_rounding_balances_zero_and_full_commission(self):
        for gross, rate, expected_net in [('100', '0', '100.00'), ('100', '100', '0.00'), ('0.05', '10', '0.05'), ('100', '33.33', '66.67')]:
            with self.subTest(gross=gross, rate=rate):
                total, commission, net = split_driver_payout(gross, rate)
                self.assertEqual(total, commission + net)
                self.assertEqual(net, Decimal(expected_net))
        for rate in ('-1', '101', 'NaN', 'Infinity'):
            with self.assertRaises(ValueError):
                split_driver_payout('100', rate)


@override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
class PayoutConcurrencyTests(PayoutFixtures, TransactionTestCase):
    def setUp(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Real row/advisory locking must be checked on PostgreSQL, not SQLite.')
        super().setUp()

    def threaded_accept(self, driver_id, barrier=None):
        connections.close_all()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '10s'")
            driver = BaseDriver.objects.select_related('user').get(pk=driver_id)
            if barrier:
                barrier.wait(timeout=10)
            result = self.client_for(driver).post(f'/api/trips/{self.trip.pk}/accept/', {}, format='json')
            return result.status_code, result.data
        finally:
            connections.close_all()

    def test_two_drivers_can_create_only_one_accepted_agreement(self):
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.threaded_accept, driver.pk, barrier) for driver in (self.driver1, self.driver2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(code for code, _ in results), [200, 400], results)
        self.trip.refresh_from_db()
        agreement = DriverPayoutAgreement.objects.get(trip=self.trip, released_at__isnull=True)
        self.assertEqual(agreement.driver_id, self.trip.base_driver_id)

    def test_acceptance_waits_for_commission_command_transaction(self):
        attempted = Event()
        real_lock = lock_commission_configuration

        def observed_lock():
            attempted.set()
            real_lock()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch('apps.trips.views.accept_trip.lock_commission_configuration', side_effect=observed_lock):
                with transaction.atomic():
                    real_lock()
                    updated = self.change('set_global', company_percentage='30.00')
                    self.assertEqual(updated.status_code, 200, updated.data)
                    future = pool.submit(self.threaded_accept, self.driver1.pk)
                    self.assertTrue(attempted.wait(timeout=10))
                    self.assertFalse(future.done())
                code, data = future.result(timeout=20)
        self.assertEqual(code, 200, data)
        self.assertEqual(DriverPayoutAgreement.objects.get(trip=self.trip).net_amount, Decimal('70.00'))
