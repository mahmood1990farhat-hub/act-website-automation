from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.pricing.models import ExtraServiceFee
from apps.vehicle.models import VehicleType
from .airport_resolver import AirportResolver


@dataclass(frozen=True)
class MeetAndGreetCharge:
    rule: Optional[ExtraServiceFee]
    amount: Decimal

    @property
    def is_available(self):
        return self.rule is not None


def is_meet_and_greet_selected(booking_details):
    if not isinstance(booking_details, dict):
        return False

    additional = booking_details.get('additional_requirements') or {}
    if not isinstance(additional, dict):
        return False

    selected = additional.get('meet_and_greet', False)
    if not isinstance(selected, bool):
        raise ValidationError({
            'booking_details': 'meet_and_greet must be true or false.'
        })
    return selected


def resolve_meet_and_greet_fee(
    vehicle_type: VehicleType,
    pickup_lat,
    pickup_lng,
    dropoff_lat,
    dropoff_lng,
    manual_airport_id=None,
    quantity=1,
):
    airport_info = AirportResolver.detect_airport(
        pickup_lat,
        pickup_lng,
        dropoff_lat,
        dropoff_lng,
        manual_airport_id,
    )
    airport_directions = {}
    pickup_airport = airport_info.get('pickup_airport')
    dropoff_airport = airport_info.get('dropoff_airport')
    if pickup_airport:
        airport_directions.setdefault(pickup_airport.id, set()).add(
            ExtraServiceFee.DIRECTION_PICKUP
        )
    if dropoff_airport:
        airport_directions.setdefault(dropoff_airport.id, set()).add(
            ExtraServiceFee.DIRECTION_DROPOFF
        )

    rules = ExtraServiceFee.objects.filter(
        service_key=ExtraServiceFee.SERVICE_MEET_GREET,
        is_active=True,
    ).filter(
        Q(vehicle_type__isnull=True) | Q(vehicle_type=vehicle_type)
    ).filter(
        Q(airport__isnull=True) | Q(airport_id__in=list(airport_directions))
    )

    candidates = []
    for rule in rules:
        if rule.airport_id:
            directions = airport_directions.get(rule.airport_id, set())
            if rule.direction != ExtraServiceFee.DIRECTION_BOTH and \
                    rule.direction not in directions:
                continue
        elif airport_directions:
            if rule.direction != ExtraServiceFee.DIRECTION_BOTH and not any(
                rule.direction in directions
                for directions in airport_directions.values()
            ):
                continue
        elif rule.direction != ExtraServiceFee.DIRECTION_BOTH:
            continue

        specificity = (
            int(rule.airport_id is not None),
            int(rule.vehicle_type_id is not None),
            int(rule.direction != ExtraServiceFee.DIRECTION_BOTH),
        )
        candidates.append((rule, specificity))

    if not candidates:
        return MeetAndGreetCharge(None, Decimal('0.00'))

    rule, _ = max(
        candidates,
        key=lambda item: (
            item[0].priority,
            item[1],
            -item[0].order,
            -item[0].pk,
        ),
    )
    amount = Decimal(str(rule.fee_amount))
    if rule.pricing_mode == ExtraServiceFee.PRICING_PER_ITEM:
        amount *= max(int(quantity or 1), 1)

    return MeetAndGreetCharge(rule, amount.quantize(Decimal('0.01')))


def apply_meet_and_greet_pricing(
    *, total_cost, booking_details, vehicle_type,
    pickup_lat, pickup_lng, dropoff_lat, dropoff_lng,
    manual_airport_id=None,
):
    selected = is_meet_and_greet_selected(booking_details)
    charge = resolve_meet_and_greet_fee(
        vehicle_type, pickup_lat, pickup_lng, dropoff_lat, dropoff_lng,
        manual_airport_id,
    )
    if selected and not charge.is_available:
        raise ValidationError({
            'meet_and_greet': 'Meet & Greet is not available for this journey and vehicle.'
        })

    applied_amount = charge.amount if selected else Decimal('0.00')
    return {
        'selected': selected,
        'available': charge.is_available,
        'rule': charge.rule,
        'meet_and_greet_fee': applied_amount,
        'meet_and_greet_total': applied_amount,
        'meet_and_greet_available_fee': charge.amount,
        'total_cost': (
            Decimal(str(total_cost)) + applied_amount
        ).quantize(Decimal('0.01')),
    }


def persist_authoritative_meet_and_greet(booking_details, pricing):
    details = dict(booking_details) if isinstance(booking_details, dict) else {}
    additional = details.get('additional_requirements') or {}
    additional = dict(additional) if isinstance(additional, dict) else {}
    additional['meet_and_greet'] = pricing['selected']
    details['additional_requirements'] = additional

    existing = details.get('extra_services') or []
    details['extra_services'] = [
        service for service in existing
        if not isinstance(service, dict) or service.get('service_key') != 'meet_greet'
    ] if isinstance(existing, list) else []

    if pricing['selected']:
        rule = pricing['rule']
        details['extra_services'].append({
            'service_key': 'meet_greet',
            'service_name': rule.service_name_en,
            'pricing_mode': rule.pricing_mode,
            'quantity': 1,
            'fee_amount': float(pricing['meet_and_greet_fee']),
            'total_amount': float(pricing['meet_and_greet_total']),
            'currency': 'GBP',
        })
    return details
