from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.pricing.models import ExtraServiceFee
from apps.pricing.services.extra_service_resolver import (
    apply_meet_and_greet_pricing,
    persist_authoritative_meet_and_greet,
    resolve_meet_and_greet_fee,
)
from apps.trips.models import Airport
from apps.vehicle.models import VehicleType


class MeetAndGreetResolverTests(TestCase):
    def setUp(self):
        self.vehicle = self.create_vehicle('Standard PHV')
        self.other_vehicle = self.create_vehicle('Executive PHV')
        self.airport = Airport.objects.create(
            name_en='Test Airport', name_ar='Test Airport',
            pickup_vat=0, dropoff_vat=0,
        )

    def create_vehicle(self, name):
        return VehicleType.objects.create(
            name_en=name, name_ar=name,
            icon='vehicle_types/icons/test.png', max_passengers_count=4,
        )

    def create_rule(self, **overrides):
        values = {
            'service_key': 'meet_greet',
            'service_name_en': 'Meet & Greet Service',
            'service_name_ar': 'Meet & Greet Service',
            'fee_amount': Decimal('20.00'),
            'pricing_mode': 'fixed_fee',
            'direction': 'both',
            'priority': 1,
            'order': 0,
            'is_active': True,
        }
        values.update(overrides)
        return ExtraServiceFee.objects.create(**values)

    def airport_result(self, pickup=False, dropoff=False):
        return {
            'pickup_airport': self.airport if pickup else None,
            'dropoff_airport': self.airport if dropoff else None,
        }

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_meet_and_greet_off_adds_no_fee(self, detect):
        detect.return_value = self.airport_result()
        self.create_rule()
        result = self.apply(selected=False)
        self.assertEqual(result['meet_and_greet_fee'], Decimal('0.00'))
        self.assertEqual(result['total_cost'], Decimal('50.00'))

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_fixed_fee_is_final_vat_inclusive_amount(self, detect):
        detect.return_value = self.airport_result()
        self.create_rule(fee_amount=Decimal('20.00'))
        result = self.apply(selected=True)
        self.assertEqual(result['meet_and_greet_fee'], Decimal('20.00'))
        self.assertEqual(result['meet_and_greet_total'], Decimal('20.00'))
        self.assertEqual(result['total_cost'], Decimal('70.00'))

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_per_item_fee_multiplies_quantity(self, detect):
        detect.return_value = self.airport_result()
        self.create_rule(pricing_mode='per_item', fee_amount=Decimal('7.50'))
        charge = resolve_meet_and_greet_fee(
            self.vehicle, 1, 1, 2, 2, quantity=2,
        )
        self.assertEqual(charge.amount, Decimal('15.00'))

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_pickup_direction_rule(self, detect):
        detect.return_value = self.airport_result(pickup=True)
        pickup = self.create_rule(direction='pickup', fee_amount=Decimal('21.00'))
        self.create_rule(direction='dropoff', fee_amount=Decimal('22.00'))
        self.assertEqual(self.resolve().rule, pickup)

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_dropoff_direction_rule(self, detect):
        detect.return_value = self.airport_result(dropoff=True)
        self.create_rule(direction='pickup', fee_amount=Decimal('21.00'))
        dropoff = self.create_rule(direction='dropoff', fee_amount=Decimal('22.00'))
        self.assertEqual(self.resolve().rule, dropoff)

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_airport_specific_rule_wins_at_equal_priority(self, detect):
        detect.return_value = self.airport_result(pickup=True)
        self.create_rule(fee_amount=Decimal('10.00'), priority=5)
        specific = self.create_rule(
            airport=self.airport, fee_amount=Decimal('25.00'), priority=5,
        )
        self.assertEqual(self.resolve().rule, specific)

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_vehicle_specific_rule_wins_at_equal_priority(self, detect):
        detect.return_value = self.airport_result()
        self.create_rule(fee_amount=Decimal('10.00'), priority=5)
        specific = self.create_rule(
            vehicle_type=self.vehicle, fee_amount=Decimal('24.00'), priority=5,
        )
        self.assertEqual(self.resolve().rule, specific)

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_inactive_rule_is_ignored(self, detect):
        detect.return_value = self.airport_result()
        self.create_rule(fee_amount=Decimal('99.00'), priority=99, is_active=False)
        active = self.create_rule(fee_amount=Decimal('20.00'), priority=1)
        self.assertEqual(self.resolve().rule, active)

    @patch('apps.pricing.services.extra_service_resolver.AirportResolver.detect_airport')
    def test_priority_then_order_selects_rule(self, detect):
        detect.return_value = self.airport_result()
        self.create_rule(fee_amount=Decimal('10.00'), priority=1, order=0)
        later = self.create_rule(fee_amount=Decimal('30.00'), priority=10, order=20)
        earlier = self.create_rule(fee_amount=Decimal('25.00'), priority=10, order=5)
        self.assertNotEqual(self.resolve().rule, later)
        self.assertEqual(self.resolve().rule, earlier)

    def test_frontend_supplied_fee_is_replaced(self):
        rule = self.create_rule(fee_amount=Decimal('20.00'))
        details = persist_authoritative_meet_and_greet(
            {
                'additional_requirements': {'meet_and_greet': True},
                'extra_services': [{'service_key': 'meet_greet', 'total_amount': 0.01}],
            },
            {
                'selected': True,
                'rule': rule,
                'meet_and_greet_fee': Decimal('20.00'),
                'meet_and_greet_total': Decimal('20.00'),
            },
        )
        self.assertEqual(details['extra_services'][0]['fee_amount'], 20.0)
        self.assertEqual(details['extra_services'][0]['total_amount'], 20.0)

    def resolve(self):
        return resolve_meet_and_greet_fee(self.vehicle, 1, 1, 2, 2)

    def apply(self, selected):
        return apply_meet_and_greet_pricing(
            total_cost=Decimal('50.00'),
            booking_details={
                'additional_requirements': {'meet_and_greet': selected},
            },
            vehicle_type=self.vehicle,
            pickup_lat=1, pickup_lng=1, dropoff_lat=2, dropoff_lng=2,
        )
