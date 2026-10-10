from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.vehicle.models import VehicleType
from apps.earnings.models import CommissionRule, DriverCommissionMembership
from apps.drivers.models import BaseDriver


class CommissionResolver:
    @staticmethod
    def get_commission_rule(vehicle_type: VehicleType = None, driver: BaseDriver = None, *, for_update=False) -> CommissionRule:
        """Resolve the existing policy without changing its legacy precedence.

        Individual DRIVER share -> active group ACT deduction -> vehicle rule ->
        configured global -> existing 20/80 fallback. Acceptance passes a freshly
        locked driver and for_update=True inside the shared commission transaction.
        """
        if driver and driver.driver_commission_percentage is not None:
            driver_percentage = driver.driver_commission_percentage
            return CommissionRule(
                company_percentage=Decimal('100.00') - driver_percentage,
                driver_percentage=driver_percentage,
            )

        memberships = DriverCommissionMembership.objects.select_related('group')
        rules = CommissionRule.objects.all()
        if for_update:
            memberships = memberships.select_for_update()
            rules = rules.select_for_update()

        if driver:
            membership = memberships.filter(driver=driver).first()
            if membership and not membership.group.is_active:
                raise ValidationError('Inactive commission group still has a driver. Release membership before resolving a new offer.')
            if membership:
                company_percentage = membership.group.company_percentage
                return CommissionRule(
                    company_percentage=company_percentage,
                    driver_percentage=Decimal('100.00') - company_percentage,
                )

        if vehicle_type:
            rule = rules.filter(vehicle_type=vehicle_type, is_active=True).first()
            if rule:
                return rule

        rule = rules.filter(vehicle_type__isnull=True, is_active=True).first()
        if rule:
            return rule

        return CommissionRule(company_percentage=Decimal('20.00'), driver_percentage=Decimal('80.00'))
