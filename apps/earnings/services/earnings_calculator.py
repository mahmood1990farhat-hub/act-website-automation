from decimal import Decimal
from typing import Tuple, Optional
from django.db import transaction
from apps.trips.models import Trip
from apps.earnings.models import DriverEarningLedger, CompanyRevenueLedger
from apps.earnings.services.commission_resolver import CommissionResolver


class EarningsCalculator:
    @staticmethod
    def calculate_and_record_earnings(trip: Trip) -> Tuple[Optional[DriverEarningLedger], CompanyRevenueLedger]:
        """
        Idempotent earnings calculation.
        Returns existing records if already calculated.
        - For trips with base_driver: driver earning + company commission.
        - For guest-driver trips (no base_driver): company revenue = full trip cost, no driver earning.
        
        Args:
            trip: Trip instance that is completed and paid
            
        Returns:
            Tuple of (DriverEarningLedger or None, CompanyRevenueLedger)
            
        Raises:
            ValueError: If trip is not in valid state for earnings calculation
        """
        if not trip.is_paid or trip.status != 'completed':
            raise ValueError("Trip must be completed and paid")
        
        # Idempotency: already recorded
        if hasattr(trip, 'company_revenue') and trip.company_revenue_id:
            driver_earning = getattr(trip, 'driver_earning', None)
            return driver_earning, trip.company_revenue
        
        currency = getattr(trip, 'currency', 'GBP')
        
        with transaction.atomic():
            if trip.base_driver:
                # System driver: commission split
                rule = CommissionResolver.get_commission_rule(
                    vehicle_type=trip.car_type,
                    driver=trip.base_driver
                )
                gross_amount = trip.cost
                commission_amount = gross_amount * (rule.company_percentage / 100)
                net_amount = gross_amount - commission_amount
                driver_earning = DriverEarningLedger.objects.create(
                    driver=trip.base_driver,
                    trip=trip,
                    gross_amount=gross_amount,
                    commission_amount=commission_amount,
                    net_amount=net_amount,
                    currency=currency,
                    status='PENDING'
                )
                company_revenue = CompanyRevenueLedger.objects.create(
                    trip=trip,
                    amount=commission_amount,
                    currency=currency
                )
                driver_earning.status = 'AVAILABLE'
                driver_earning.save(update_fields=['status'])
                return driver_earning, company_revenue
            else:
                # Guest driver: full trip cost to company, no driver ledger
                company_revenue = CompanyRevenueLedger.objects.create(
                    trip=trip,
                    amount=trip.cost,
                    currency=currency
                )
                return None, company_revenue

