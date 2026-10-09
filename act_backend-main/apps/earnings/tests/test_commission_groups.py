from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.drivers.models import BaseDriver
from apps.earnings.models import DriverCommissionGroup, DriverCommissionMembership, CommissionRule
from apps.earnings.services.commission_resolver import CommissionResolver


class CommissionGroupTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="commission-group-driver", email="group@example.invalid",
            password="test-password", first_name="Test", last_name="Driver",
            account_type="normal_driver", address="Test",
        )
        self.driver = BaseDriver.objects.create(
            user=user, pco="test.pdf", dbs="test.pdf", dvla="test.pdf",
        )
        self.group = DriverCommissionGroup.objects.create(
            name="DSS", company_percentage=Decimal("15.00"),
        )

    def test_group_rate_resolves_to_company_deduction(self):
        DriverCommissionMembership.objects.create(driver=self.driver, group=self.group)
        rule = CommissionResolver.get_commission_rule(driver=self.driver)
        self.assertEqual(rule.company_percentage, Decimal("15.00"))
        self.assertEqual(rule.driver_percentage, Decimal("85.00"))

    def test_group_rejects_individual_override(self):
        self.driver.driver_commission_percentage = Decimal("75.00")
        self.driver.save()
        with self.assertRaises(ValidationError):
            DriverCommissionMembership.objects.create(driver=self.driver, group=self.group)

    def test_individual_override_rejects_grouped_driver(self):
        DriverCommissionMembership.objects.create(driver=self.driver, group=self.group)
        self.driver.driver_commission_percentage = Decimal("75.00")
        with self.assertRaises(ValidationError):
            self.driver.save()

    def test_driver_cannot_join_two_groups(self):
        DriverCommissionMembership.objects.create(driver=self.driver, group=self.group)
        other = DriverCommissionGroup.objects.create(
            name="Other", company_percentage=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            DriverCommissionMembership.objects.create(driver=self.driver, group=other)

    def test_global_fallback_unchanged(self):
        rule = CommissionResolver.get_commission_rule(driver=self.driver)
        self.assertEqual(rule.company_percentage, Decimal("20.00"))
        self.assertEqual(rule.driver_percentage, Decimal("80.00"))

    def test_group_percentage_bounds(self):
        for rate in (Decimal("-1"), Decimal("101")):
            with self.assertRaises(ValidationError):
                DriverCommissionGroup.objects.create(name="Invalid", company_percentage=rate)
