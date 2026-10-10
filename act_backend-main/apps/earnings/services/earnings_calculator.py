from typing import Tuple, Optional
from django.db import transaction
from apps.trips.models import Trip
from apps.earnings.models import DriverEarningLedger, CompanyRevenueLedger, DriverPayoutAgreement
from apps.earnings.services.commission_resolver import CommissionResolver


class EarningsCalculator:
    @staticmethod
    def calculate_and_record_earnings(trip: Trip) -> Tuple[Optional[DriverEarningLedger], CompanyRevenueLedger]:
        """Idempotent completion: use accepted terms, never today's rate instead.

        Existing settled ledgers and the historical no-agreement path are retained.
        No agreement is backfilled using an invented historical acceptance rate.
        """
        with transaction.atomic():
            # Also protects callers outside CompleteTripView and repeated repairs.
            trip = Trip.objects.select_for_update().get(pk=trip.pk)
            if not trip.is_paid or trip.status != 'completed':
                raise ValueError('Trip must be completed and paid')
            company_revenue = CompanyRevenueLedger.objects.filter(trip=trip).first()
            if company_revenue is not None:
                driver_earning = DriverEarningLedger.objects.filter(trip=trip).first()
                return driver_earning, company_revenue

            currency = getattr(trip, 'currency', 'GBP')
            if trip.base_driver:
                agreement = DriverPayoutAgreement.objects.filter(trip=trip, released_at__isnull=True).first()
                if agreement:
                    if agreement.driver_id != trip.base_driver_id or agreement.gross_amount != trip.cost or agreement.currency != currency:
                        raise ValueError('Accepted payout terms do not match this journey. Finance review is required.')
                    gross_amount = agreement.gross_amount
                    commission_amount = agreement.commission_amount
                    net_amount = agreement.net_amount
                else:
                    if DriverPayoutAgreement.objects.filter(trip=trip).exists():
                        raise ValueError('Released payout terms cannot be repriced or paid to another driver.')
                    # Legacy journey with no captured acceptance: preserve old behaviour.
                    # New admin rate changes remain blocked for unfinished such journeys.
                    rule = CommissionResolver.get_commission_rule(vehicle_type=trip.car_type, driver=trip.base_driver)
                    gross_amount = trip.cost
                    commission_amount = gross_amount * (rule.company_percentage / 100)
                    net_amount = gross_amount - commission_amount

                driver_earning = DriverEarningLedger.objects.create(
                    driver=trip.base_driver, trip=trip, gross_amount=gross_amount,
                    commission_amount=commission_amount, net_amount=net_amount,
                    currency=currency, status='PENDING',
                )
                company_revenue = CompanyRevenueLedger.objects.create(trip=trip, amount=commission_amount, currency=currency)
                driver_earning.status = 'AVAILABLE'
                driver_earning.save(update_fields=['status'])
                return driver_earning, company_revenue

            # Existing guest-driver settlement behaviour is deliberately unchanged.
            company_revenue = CompanyRevenueLedger.objects.create(trip=trip, amount=trip.cost, currency=currency)
            return None, company_revenue
