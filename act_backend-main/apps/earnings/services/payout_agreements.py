"""Accepted payout terms; no Stripe calls, payouts or customer fare writes."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection
from django.db.transaction import TransactionManagementError
from django.utils import timezone

from apps.earnings.models import DriverPayoutAgreement, DriverEarningLedger, CompanyRevenueLedger
from apps.earnings.services.commission_resolver import CommissionResolver

PENNY = Decimal('0.01')
HUNDRED = Decimal('100.00')
AGREED_STATES = ('accepted', 'driver_on_the_way', 'active', 'completed')


def split_driver_payout(gross, company_percentage):
    gross = Decimal(str(gross))
    rate = Decimal(str(company_percentage))
    if not gross.is_finite() or gross < 0 or not rate.is_finite() or not 0 <= rate <= HUNDRED:
        raise ValueError('Invalid fare or commission percentage.')
    gross = gross.quantize(PENNY, rounding=ROUND_HALF_UP)
    net = (gross * (HUNDRED - rate) / HUNDRED).quantize(PENNY, rounding=ROUND_HALF_UP)
    return gross, gross - net, net


def capture_driver_payout(trip, driver):
    """Caller holds commission lock, fresh driver row and trip row, in that order.

    Called only after the normal acceptance eligibility checks. The caller saves
    accepted state in the same transaction. A pending re-offer creates NEW terms;
    an earlier agreement is retained as released history, never overwritten.
    """
    if not connection.in_atomic_block:
        raise TransactionManagementError('Payout capture requires locked acceptance.')
    if trip.status != 'pending' or not trip.is_paid:
        raise ValueError('Only a paid pending journey can acquire payout terms.')
    if trip.base_driver_id not in (None, driver.pk):
        raise ValueError('Journey belongs to another driver.')
    if CompanyRevenueLedger.objects.filter(trip=trip).exists() or DriverEarningLedger.objects.filter(trip=trip).exists():
        raise ValueError('A settled journey cannot acquire a new driver agreement.')
    rule = CommissionResolver.get_commission_rule(vehicle_type=trip.car_type, driver=driver, for_update=True)
    gross, commission, net = split_driver_payout(trip.cost, rule.company_percentage)
    release_driver_payout(trip)
    return DriverPayoutAgreement.objects.create(
        trip=trip, driver=driver, gross_amount=gross,
        company_percentage=rule.company_percentage, commission_amount=commission,
        net_amount=net, currency=getattr(trip, 'currency', 'GBP'),
    )


def release_driver_payout(trip):
    """Call while holding the trip row; financial terms remain immutable."""
    if not connection.in_atomic_block:
        raise TransactionManagementError('Payout release requires a locked trip transaction.')
    return DriverPayoutAgreement.objects.filter(trip=trip, released_at__isnull=True).update(released_at=timezone.now())


def agreed_payout_for_driver(trip, driver):
    if not driver or trip.base_driver_id != driver.pk or trip.status not in AGREED_STATES:
        return None
    return DriverPayoutAgreement.objects.filter(trip=trip, driver=driver, released_at__isnull=True).first()


def driver_payout_display(trip, driver):
    """Return (net amount, legacy driver-share percentage), not the customer fare.

    Caller retains its existing driver-only context check. Already accepted
    amounts take precedence over current policy. No historical agreement is
    invented for legacy journeys that predate this feature.
    """
    if driver is None or trip.cost is None:
        return None, None
    if trip.base_driver_id not in (None, driver.pk):
        return None, None
    agreement = agreed_payout_for_driver(trip, driver)
    if agreement:
        return agreement.net_amount, HUNDRED - agreement.company_percentage
    if trip.status == 'completed':
        ledger = DriverEarningLedger.objects.filter(trip=trip, driver=driver).first()
        if ledger:
            percentage = (ledger.net_amount / ledger.gross_amount * HUNDRED) if ledger.gross_amount else None
            return ledger.net_amount, percentage
    rule = CommissionResolver.get_commission_rule(vehicle_type=trip.car_type, driver=driver)
    _, _, net = split_driver_payout(trip.cost, rule.company_percentage)
    return net, rule.driver_percentage
