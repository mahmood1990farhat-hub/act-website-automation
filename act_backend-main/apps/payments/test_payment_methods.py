from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from apps.payments.models import PendingPayment
from apps.payments.views.views import create_trip_from_payment, extract_card_details, stripe_webhook_view
from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


class PaymentMethodExtractionTests(SimpleTestCase):
    def test_extracts_card_brand_and_last_four(self):
        payment_intent = {
            'charges': {
                'data': [{
                    'payment_method_details': {
                        'type': 'card',
                        'card': {'brand': 'visa', 'last4': '4242'},
                    },
                }],
            },
        }

        self.assertEqual(extract_card_details(payment_intent), {
            'last4': '4242',
            'card_brand': 'visa',
            'payment_method_type': 'card',
        })

    def test_extracts_clearpay_from_expanded_charge(self):
        payment_intent = {
            'latest_charge': {
                'payment_method_details': {'type': 'afterpay_clearpay'},
            },
        }

        self.assertEqual(extract_card_details(payment_intent), {
            'last4': None,
            'card_brand': 'Clearpay',
            'payment_method_type': 'afterpay_clearpay',
        })

    @patch('apps.payments.views.views.stripe.Charge.retrieve')
    def test_extracts_clearpay_when_latest_charge_is_an_id(self, retrieve_charge):
        retrieve_charge.return_value = {
            'payment_method_details': {'type': 'afterpay_clearpay'},
        }

        details = extract_card_details({'latest_charge': 'ch_clearpay'})

        retrieve_charge.assert_called_once_with('ch_clearpay')
        self.assertEqual(details['card_brand'], 'Clearpay')
        self.assertEqual(details['payment_method_type'], 'afterpay_clearpay')


class StripeWebhookRoutingTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().post(
            '/api/payments/webhook/stripe/',
            data=b'{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test-signature',
        )

    @patch('apps.payments.views.views.handle_payment_succeeded')
    @patch('apps.payments.views.views.stripe.Webhook.construct_event')
    def test_succeeded_event_enters_booking_creation_flow(self, construct_event, handle_succeeded):
        event = {
            'type': 'payment_intent.succeeded',
            'data': {'object': {'id': 'pi_succeeded', 'metadata': {'pending_payment_id': '1'}}},
        }
        construct_event.return_value = event

        response = stripe_webhook_view(self.request)

        self.assertEqual(response.status_code, 200)
        handle_succeeded.assert_called_once_with(event)

    @patch('apps.payments.views.views.handle_payment_succeeded')
    @patch('apps.payments.views.views.stripe.Webhook.construct_event')
    def test_processing_event_does_not_create_booking(self, construct_event, handle_succeeded):
        construct_event.return_value = {
            'type': 'payment_intent.processing',
            'data': {'object': {'id': 'pi_processing', 'metadata': {'pending_payment_id': '1'}}},
        }

        response = stripe_webhook_view(self.request)

        self.assertEqual(response.status_code, 200)
        handle_succeeded.assert_not_called()


class PendingPaymentLifecycleTests(TestCase):
    def create_pending(self, payment_intent_id, expires_at):
        return PendingPayment.objects.create(
            payment_intent_id=payment_intent_id,
            price_breakdown={},
            trip_data={},
            expires_at=expires_at,
        )

    def test_cleanup_removes_only_expired_pending_payments(self):
        expired = self.create_pending('pi_expired', timezone.now() - timedelta(minutes=1))
        current = self.create_pending('pi_current', timezone.now() + timedelta(hours=4))

        call_command('cleanup_expired_payments', verbosity=0)

        self.assertFalse(PendingPayment.objects.filter(id=expired.id).exists())
        self.assertTrue(PendingPayment.objects.filter(id=current.id).exists())

    @patch('apps.payments.views.views.calculate_route_safe', return_value={})
    def test_succeeded_clearpay_payment_creates_trip_and_deletes_pending(self, _route):
        vehicle = VehicleType.objects.create(
            name_en='Standard PHV',
            name_ar='Standard PHV',
            icon='vehicle_types/icons/test.png',
            max_passengers_count=4,
        )
        pending = PendingPayment.objects.create(
            payment_intent_id='pi_clearpay',
            passenger_name='Guest Passenger',
            passenger_email='guest@example.com',
            passenger_country_code='+44',
            passenger_phone='7000000000',
            booking_details={'additional_requirements': {'notes_to_driver': 'Test note'}},
            price_breakdown={
                'total_cost': 50,
                'base_trip_cost': 40,
                'regular_vat': 10,
                'airport_vat': 0,
                'min_adjustment': 0,
            },
            trip_data={
                'pickup_lat': 51.5,
                'pickup_lng': -0.1,
                'dropoff_lat': 51.6,
                'dropoff_lng': -0.2,
                'trip_date': '2030-01-01',
                'trip_time': '10:00',
                'passengers_count': 1,
                'large_suitcase': 0,
                'small_suitcase': 0,
                'car_type': vehicle.id,
            },
            expires_at=timezone.now() + timedelta(hours=4),
        )
        payment_intent = {
            'id': 'pi_clearpay',
            'charges': {'data': [{
                'payment_method_details': {'type': 'afterpay_clearpay'},
            }]},
        }

        trip = create_trip_from_payment(payment_intent, pending.id)

        self.assertEqual(trip.card_brand, 'Clearpay')
        self.assertIsNone(trip.last4)
        self.assertTrue(trip.is_guest_checkout)
        self.assertTrue(trip.is_paid)
        self.assertEqual(trip.booking_details['additional_requirements']['notes_to_driver'], 'Test note')
        self.assertFalse(PendingPayment.objects.filter(id=pending.id).exists())
        self.assertTrue(Trip.objects.filter(stripe_payment_intent='pi_clearpay').exists())
