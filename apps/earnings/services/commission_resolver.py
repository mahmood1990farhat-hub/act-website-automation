from decimal import Decimal
from apps.vehicle.models import VehicleType
from apps.earnings.models import CommissionRule
from apps.drivers.models import BaseDriver


class CommissionResolver:
    @staticmethod
    def get_commission_rule(vehicle_type: VehicleType = None, driver: BaseDriver = None) -> CommissionRule:
        """
        Get the appropriate commission rule for a vehicle type and/or driver.
        
        Priority order:
        1. Driver-specific percentage (if driver has driver_commission_percentage set)
        2. Vehicle type rule
        3. Global default rule
        4. Hardcoded default (80/20)
        
        Args:
            vehicle_type: VehicleType instance or None
            driver: BaseDriver instance or None
            
        Returns:
            CommissionRule instance (or default if none found)
        """
        # Priority 1: Check if driver has custom percentage
        if driver and driver.driver_commission_percentage is not None:
            driver_percentage = driver.driver_commission_percentage
            company_percentage = Decimal('100.00') - driver_percentage
            # Return a non-persisted instance for calculation
            return CommissionRule(
                company_percentage=company_percentage,
                driver_percentage=driver_percentage
            )
        
        # Priority 2: Try vehicle-specific rule
        if vehicle_type:
            rule = CommissionRule.objects.filter(
                vehicle_type=vehicle_type,
                is_active=True
            ).first()
            
            if rule:
                return rule
        
        # Priority 3: Fall back to global rule (vehicle_type=None)
        rule = CommissionRule.objects.filter(
            vehicle_type__isnull=True,
            is_active=True
        ).first()
        
        if rule:
            return rule
        
        # Priority 4: Default: 20/80 split (return a non-persisted instance for calculation)
        # Note: This should ideally be created via migration, but this is a fallback
        return CommissionRule(
            company_percentage=Decimal('20.00'),
            driver_percentage=Decimal('80.00')
        )

