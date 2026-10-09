from datetime import date, time
from decimal import Decimal
import json

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.drivers.models import BaseDriver
from apps.earnings.models import CommissionRule, DriverCommissionGroup, DriverCommissionMembership
from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


class CommissionManagementTests(TestCase):
    url = '/api/admin-panel/commission-management/'

    def setUp(self):
        self.admin = self.user('commission-admin', 'admin')
        self.admin.is_staff = True
        self.admin.save()
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.drivers = [BaseDriver.objects.create(
            user=self.user('commission-driver-' + str(index), 'normal_driver'),
            pco='test.pdf', dbs='test.pdf', dvla='test.pdf',
        ) for index in range(4)]

    def user(self, name, kind):
        return get_user_model().objects.create_user(
            username=name, email=name + '@example.invalid', password='test-only',
            first_name='Test', last_name=name, account_type=kind, address='Test',
        )

    def snapshot(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        return response.data['data']

    def command(self, action, **fields):
        body = {'action': action, 'revision': self.snapshot()['revision'], 'reason': 'Isolated test'}
        body.update(fields)
        return self.client.post(self.url, body, format='json')

    def test_anonymous_and_driver_cannot_read_or_write_admin_finance(self):
        for user in [None, self.drivers[0].user]:
            self.client.force_authenticate(user=user)
            for method in [self.client.get, self.client.post]:
                response = method(self.url, {}, format='json')
                self.assertIn(response.status_code, [401, 403])

    def test_write_gate_defaults_closed_even_for_admin(self):
        self.assertFalse(self.snapshot()['writes_enabled'])
        response = self.command('set_global', company_percentage='25')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CommissionRule.objects.exists())
        self.assertFalse(LogEntry.objects.filter(object_repr='ACT commission management').exists())

    def test_snapshot_partitions_every_driver_once_including_zero_share(self):
        driver = self.drivers[1]
        driver.driver_commission_percentage = Decimal('0.00')
        driver.save()
        group = DriverCommissionGroup.objects.create(name='DSS', company_percentage=Decimal('15.00'))
        DriverCommissionMembership.objects.create(driver=self.drivers[2], group=group)
        data = self.snapshot()
        rows = {row['id']: row for row in data['drivers']}
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[self.drivers[0].id]['category'], 'global')
        self.assertEqual(rows[driver.id]['category'], 'individual')
        self.assertEqual(rows[driver.id]['company_percentage'], '100.00')
        self.assertEqual(rows[self.drivers[2].id]['category'], 'group')
        self.assertEqual(rows[self.drivers[2].id]['company_percentage'], '15.00')

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_inactive_group_member_is_flagged_and_cannot_silently_fallback(self):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from apps.earnings.services.commission_resolver import CommissionResolver
        group = DriverCommissionGroup.objects.create(
            name='Inactive DSS', company_percentage=Decimal('15.00'), is_active=False,
        )
        DriverCommissionMembership.objects.create(driver=self.drivers[0], group=group)
        data = self.snapshot()
        member = next(row for row in data['drivers'] if row['id'] == self.drivers[0].id)
        self.assertEqual(member['category'], 'conflict')
        self.assertIsNone(member['company_percentage'])
        self.assertIn(self.drivers[0].id, data['conflicting_driver_ids'])
        with self.assertRaises(DjangoValidationError):
            CommissionResolver.get_commission_rule(driver=self.drivers[0])
        response = self.command('set_global', company_percentage='25.00')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(CommissionRule.objects.exists())

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_global_change_excludes_individual_and_group_drivers(self):
        driver = self.drivers[1]
        driver.driver_commission_percentage = Decimal('75.00')
        driver.save()
        group = DriverCommissionGroup.objects.create(name='DSS', company_percentage=Decimal('10.00'))
        DriverCommissionMembership.objects.create(driver=self.drivers[2], group=group)
        response = self.command('set_global', company_percentage='20.00')
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row['id']: row for row in response.data['data']['drivers']}
        self.assertEqual(rows[self.drivers[0].id]['company_percentage'], '20.00')
        self.assertEqual(rows[driver.id]['company_percentage'], '25.00')
        self.assertEqual(rows[self.drivers[2].id]['company_percentage'], '10.00')
        audit = LogEntry.objects.get(object_repr='ACT commission management')
        self.assertEqual(audit.user_id, self.admin.id)
        self.assertEqual(json.loads(audit.change_message)['reason'], 'Isolated test')

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_individual_control_converts_act_deduction_to_driver_share(self):
        response = self.command('set_individual', driver_ids=[self.drivers[0].id], company_percentage='25.00')
        self.assertEqual(response.status_code, 200, response.data)
        self.drivers[0].refresh_from_db()
        self.assertEqual(self.drivers[0].driver_commission_percentage, Decimal('75.00'))
        response = self.command('clear_individual', driver_ids=[self.drivers[0].id])
        self.assertEqual(response.status_code, 200, response.data)
        self.drivers[0].refresh_from_db()
        self.assertIsNone(self.drivers[0].driver_commission_percentage)

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_create_group_add_release_and_change_rate(self):
        response = self.command('create_group', name='DSS', company_percentage='15', driver_ids=[self.drivers[0].id, self.drivers[1].id])
        self.assertEqual(response.status_code, 200, response.data)
        group = DriverCommissionGroup.objects.get(name='DSS')
        response = self.command('add_members', group_id=group.id, driver_ids=[self.drivers[2].id])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(group.memberships.count(), 3)
        response = self.command('set_group_rate', group_id=group.id, company_percentage='10')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.command('release_members', group_id=group.id, driver_ids=[self.drivers[0].id])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(DriverCommissionMembership.objects.filter(driver=self.drivers[0]).exists())
        group.refresh_from_db()
        self.assertEqual(group.company_percentage, Decimal('10.00'))
        self.assertEqual(group.memberships.count(), 2)

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_conflicting_bulk_membership_is_all_or_nothing(self):
        self.drivers[0].driver_commission_percentage = Decimal('80.00')
        self.drivers[0].save()
        response = self.command('create_group', name='DSS', company_percentage='15', driver_ids=[self.drivers[1].id, self.drivers[0].id])
        self.assertEqual(response.status_code, 409, response.data)
        self.assertFalse(DriverCommissionGroup.objects.exists())
        self.assertFalse(DriverCommissionMembership.objects.exists())

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_grouped_driver_cannot_become_individual_or_join_another_group(self):
        group = DriverCommissionGroup.objects.create(name='DSS', company_percentage=Decimal('15.00'))
        DriverCommissionMembership.objects.create(driver=self.drivers[0], group=group)
        response = self.command('set_individual', driver_ids=[self.drivers[0].id], company_percentage='25')
        self.assertEqual(response.status_code, 409, response.data)
        response = self.command('create_group', name='Other', driver_ids=[self.drivers[0].id], company_percentage='20')
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(DriverCommissionMembership.objects.count(), 1)
        self.drivers[0].refresh_from_db()
        self.assertIsNone(self.drivers[0].driver_commission_percentage)

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_stale_revision_cannot_overwrite_newer_rate(self):
        previous = self.snapshot()['revision']
        self.assertEqual(self.command('set_global', company_percentage='25').status_code, 200)
        response = self.command('set_global', company_percentage='10', revision=previous)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.snapshot()['global_percentage'], '25.00')

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_rejects_invalid_rates_ids_unknown_fields_and_missing_reason(self):
        for rate in ['-1', '100.01', '1.001', 'NaN', 'Infinity', 'text', '']:
            with self.subTest(rate=rate):
                self.assertEqual(self.command('set_global', company_percentage=rate).status_code, 400)
        self.assertEqual(self.command('set_individual', driver_ids=[self.drivers[0].id] * 2, company_percentage='20').status_code, 400)
        self.assertEqual(self.command('set_individual', driver_ids=[999999], company_percentage='20').status_code, 400)
        self.assertEqual(self.command('set_global', company_percentage='20', reason=' ').status_code, 400)
        self.assertEqual(self.command('set_global', company_percentage='20', driver_ids=[self.drivers[0].id]).status_code, 400)
        self.assertFalse(CommissionRule.objects.exists())

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_zero_and_hundred_are_valid_act_deductions(self):
        for rate, expected_share in [('0', Decimal('100.00')), ('100', Decimal('0.00'))]:
            response = self.command('set_individual', driver_ids=[self.drivers[0].id], company_percentage=rate)
            self.assertEqual(response.status_code, 200, response.data)
            self.drivers[0].refresh_from_db()
            self.assertEqual(self.drivers[0].driver_commission_percentage, expected_share)

    def vehicle(self):
        return VehicleType.objects.create(code='comfort', name_en='Comfort', name_ar='Comfort',
            icon='vehicle_types/icons/test.png', max_passengers_count=4)

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_legacy_vehicle_rule_is_not_silently_overwritten(self):
        rule = CommissionRule.objects.create(vehicle_type=self.vehicle(), company_percentage=Decimal('30.00'), driver_percentage=Decimal('70.00'))
        response = self.command('set_global', company_percentage='20')
        self.assertEqual(response.status_code, 409, response.data)
        rule.refresh_from_db()
        self.assertEqual(rule.company_percentage, Decimal('30.00'))
        self.assertFalse(CommissionRule.objects.filter(vehicle_type__isnull=True).exists())

    @override_settings(ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED=True)
    def test_unfinished_assigned_journey_blocks_affected_rate_changes(self):
        Trip.objects.create(pickup_lat=51.47, pickup_lng=-0.45, dropoff_lat=51.5, dropoff_lng=-0.12,
            trip_date=date.today(), trip_time=time(12), car_type=self.vehicle(), cost=Decimal('100.00'),
            passengers_count=1, status='accepted', is_paid=True, base_driver=self.drivers[0])
        response = self.command('set_individual', driver_ids=[self.drivers[0].id], company_percentage='30')
        self.assertEqual(response.status_code, 409, response.data)
        self.drivers[0].refresh_from_db()
        self.assertIsNone(self.drivers[0].driver_commission_percentage)
        self.assertEqual(self.command('set_global', company_percentage='30').status_code, 409)
