from decimal import Decimal
from typing import Tuple, Optional
from django.db import transaction
from apps.trips.models import Trip
from apps.earnings.models import DriverEarningLedger, DriverRefundLedger, CompanyRefundLedger
import uuid


class RefundRulesService:
    """
    Determines refund rules based on earnings payout status.
    """
    
    @staticmethod
    def determine_refund_rule(driver_earning: DriverEarningLedger) -> str:
        """
        Determine refund rule based on earnings status.
        
        Rules:
        - PENDING/AVAILABLE: Full refund (earnings not yet paid)
        - LOCKED/PROCESSING: No refund (payout in progress, must handle manually)
        - PAID: No refund (earnings already paid to driver)
        
        Args:
            driver_earning: DriverEarningLedger instance
            
        Returns:
            Refund rule string: 'FULL_REFUND', 'PARTIAL_REFUND', or 'NO_REFUND'
        """
        if driver_earning.status in ['PENDING', 'AVAILABLE']:
            return 'FULL_REFUND'
        elif driver_earning.status in ['LOCKED', 'PROCESSING']:
            return 'NO_REFUND'  # Manual intervention required
        elif driver_earning.status == 'PAID':
            return 'NO_REFUND'  # Already paid, cannot refund driver portion
        else:
            return 'NO_REFUND'
    
    @staticmethod
    def process_refund(trip: Trip, refund_amount: Decimal, stripe_refund_id: str) -> Tuple[Optional[DriverRefundLedger], CompanyRefundLedger]:
        """
        Process refund and create appropriate ledger entries.
        
        Args:
            trip: Trip instance being refunded
            refund_amount: Positive refund amount (will be stored as negative)
            stripe_refund_id: Stripe refund ID
            
        Returns:
            Tuple of (DriverRefundLedger or None, CompanyRefundLedger)
        """
        driver_earning = getattr(trip, 'driver_earning', None)
        currency = getattr(trip, 'currency', 'GBP')
        
        with transaction.atomic():
            # Determine refund rule
            if driver_earning:
                refund_rule = RefundRulesService.determine_refund_rule(driver_earning)
            else:
                refund_rule = 'FULL_REFUND'  # No earnings calculated yet
            
            # Create driver refund ledger entry
            driver_refund = None
            if trip.base_driver and refund_rule == 'FULL_REFUND':
                idempotency_key = f"driver_refund_{trip.id}_{uuid.uuid4().hex}"
                driver_refund = DriverRefundLedger.objects.create(
                    driver=trip.base_driver,
                    trip=trip,
                    driver_earning=driver_earning,
                    refund_amount=-refund_amount,  # Always negative
                    currency=currency,
                    refund_rule=refund_rule,
                    stripe_refund_id=stripe_refund_id,
                    stripe_idempotency_key=idempotency_key
                )
                
                # If earnings exist and not paid, mark as voided/reversed
                if driver_earning and driver_earning.status in ['PENDING', 'AVAILABLE']:
                    # Option: Create negative earning entry or mark status
                    # For now, refund ledger entry is sufficient
                    pass
            
            # Create company refund ledger entry (always refund company commission)
            company_refund_idempotency_key = f"company_refund_{trip.id}_{uuid.uuid4().hex}"
            company_refund = CompanyRefundLedger.objects.create(
                trip=trip,
                refund_amount=-refund_amount,  # Full refund amount (company portion already deducted)
                currency=currency,
                stripe_refund_id=stripe_refund_id,
                stripe_idempotency_key=company_refund_idempotency_key
            )
            
            return driver_refund, company_refund

