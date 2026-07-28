from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.payments.models import PendingPayment
from apps.pricing.models import ExtraServiceFee
from apps.trips.views.calculate_trip_cost import CalculateTripCostView
from apps.trips.views.initiate_payment import (
    InitiateGuestPaymentView,
    InitiatePaymentView,
    calculate_authoritative_payment_price,
)
from apps.vehicle.models import VehicleType


class MeetAndGreetQuoteAndPaymentTests(TestCase):
    def setUp(self):
        self.vehicle = VehicleType.objects.create(
            name_en='Standard PHV', name_ar='Standard PHV',
            icon='vehicle_types/icons/test.png', max_passengers_count=4,
        )
        ExtraServiceFee.objects.create(
            service_key='meet_greet',
            service_name_en='Meet & Greet Service',
            service_name_ar='Meet & Greet Service',
            fee_amount=Decimal('20.00'),
            pricing_mode='fixed_fee', direction='both',
            priority=1, is_active=True,
        )
        self.request_data = {
            'pickup_location': {'lat': 51.5, 'lng': -0.1},
            'dropoff_location': {'lat': 51.6, 'lng': -0.2},
            'trip_date': '2030-01-01',
            'trip_time': '10:00',
            'passengers_count': 1,
            'large_suitcase': 0,
            'small_suitcase': 0,
            'car_type': self.vehicle.id,
            'passenger_name': 'Test Passenger',
            'passenger_email': 'passenger@example.com',
            'passenger_country_code': '+44',
            'passenger_phone': '7000000000',
            'booking_details': {
                'additional_requirements': {'meet_and_greet': True},
                'extra_services': [
                    {'service_key': 'meet_greet', 'total_amount': 0.01},
                ],
            },
        }
        self.prepared_data = {
            'pickup_lat': 51.5,
            'pickup_lng': -0.1,
            'dropoff_lat': 51.6,
            'dropoff_lng': -0.2,
            'trip_date': '2030-01-01',
            'trip_time': '10:00',
            'passengers_count': 1,
            'large_suitcase': 0,
            'small_suitcase': 0,
            'car_type': self.vehicle.id,
        }

    def pricing_patches(self):
        return (
            patch(
                'apps.pricing.services.extra_service_resolver.'
                'AirportResolver.detect_airport',
                return_value={'pickup_airport': None, 'dropoff_airport': None},
            ),
            patch(
                'apps.trips.views.initiate_payment.calculate_total_cost',
                return_value=(
                    Decimal('50.00'), Decimal('8.00'), Decimal('0.00'),
                    Decimal('42.00'), Decimal('0.00'),
                ),
            ),
        )

    def test_authenticated_payment_recalculates_authoritative_fee(self):
        response, stripe_create = self.run_payment(guest=False)
        pending = PendingPayment.objects.get(id=response.data['pending_payment_id'])
        self.assertEqual(response.data['price_breakdown']['total_cost'], 70.0)
        self.assertEqual(pending.price_breakdown['meet_and_greet_fee'], 20.0)
        self.assertEqual(pending.booking_details['extra_services'][0]['total_amount'], 20.0)
        self.assertEqual(stripe_create.call_args.kwargs['amount'], 7000)

    def test_guest_payment_recalculates_same_authoritative_fee(self):
        response, stripe_create = self.run_payment(guest=True)
        pending = PendingPayment.objects.get(id=response.data['pending_payment_id'])
        self.assertIsNone(pending.passenger_id)
        self.assertEqual(response.data['price_breakdown']['total_cost'], 70.0)
        self.assertEqual(pending.price_breakdown['meet_and_greet_total'], 20.0)
        self.assertEqual(stripe_create.call_args.kwargs['amount'], 7000)

    def test_quote_and_payment_totals_match(self):
        serializer = Mock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            'trip_time': time(10, 0),
            'trip_date': date(2030, 1, 1),
            'passengers_count': 1,
        }
        quote_request = SimpleNamespace(
            data=self.request_data,
            build_absolute_uri=lambda path: f'https://example.com{path}',
        )
        with patch(
            'apps.trips.views.calculate_trip_cost.prepare_trip_data',
            return_value=self.prepared_data.copy(),
        ), patch(
            'apps.trips.views.calculate_trip_cost.TripSerializer',
            return_value=serializer,
        ), patch(
            'apps.trips.views.calculate_trip_cost.get_route_with_distance',
            return_value=self.route_result(),
        ), patch(
            'apps.trips.views.calculate_trip_cost.calculate_total_cost',
            return_value=(
                Decimal('50.00'), Decimal('8.00'), Decimal('0.00'),
                Decimal('42.00'), Decimal('0.00'),
            ),
        ), patch(
            'apps.pricing.services.extra_service_resolver.'
            'AirportResolver.detect_airport',
            return_value={'pickup_airport': None, 'dropoff_airport': None},
        ):
            quote = CalculateTripCostView()._handle_post(quote_request, [])

        with self.pricing_patches()[0], self.pricing_patches()[1]:
            payment_total, breakdown, _, _, _ = calculate_authoritative_payment_price(
                self.prepared_data,
                self.vehicle,
                10,
                self.request_data['booking_details'],
            )

        quoted_total = quote.data['car_type'][0]['total_cost']
        self.assertEqual(quoted_total, payment_total)
        self.assertEqual(float(quoted_total), breakdown['total_cost'])

    def run_payment(self, guest):
        request = SimpleNamespace(data=self.request_data.copy())
        if not guest:
            request.user = SimpleNamespace(
                passenger_profile=SimpleNamespace(id=123),
                first_name='Test', last_name='Passenger',
                email='passenger@example.com',
            )
        payment_intent = SimpleNamespace(id='pi_test', client_secret='secret_test')
        view = InitiateGuestPaymentView() if guest else InitiatePaymentView()
        with patch(
            'apps.trips.views.initiate_payment.get_locale', return_value='en',
        ), patch(
            'apps.trips.views.initiate_payment.prepare_trip_data',
            return_value=self.prepared_data.copy(),
        ), patch(
            'apps.trips.views.initiate_payment.get_route_with_distance',
            return_value=self.route_result(),
        ), self.pricing_patches()[0], self.pricing_patches()[1], patch(
            'apps.trips.views.initiate_payment.stripe.PaymentIntent.create',
            return_value=payment_intent,
        ) as stripe_create, patch(
            'apps.trips.views.initiate_payment.stripe.PaymentIntent.modify',
        ):
            response = view.handle_post(request)
        return response, stripe_create

    @staticmethod
    def route_result():
        return {
            'distance_miles': 10,
            'distance_meters': 16093,
            'duration_minutes': 30,
            'route_polyline': 'encoded-route',
        }
