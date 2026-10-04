from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.payments.models import PendingPayment
from apps.payments.views.views import (
    get_pending_payment,
    handle_payment_succeeded,
    stripe_webhook_view,
    verify_payment_matches_pending,
)


class StripeWebhookReliabilityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    @patch("apps.payments.views.views.handle_payment_succeeded")
    @patch("apps.payments.views.views.stripe.Webhook.construct_event")
    def test_verified_event_returns_500_when_booking_processing_fails(
        self, construct_event, handle_success
    ):
        construct_event.return_value = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_retry", "metadata": {}}},
        }
        handle_success.side_effect = RuntimeError("database unavailable")
        request = self.factory.post(
            "/api/payments/webhook/stripe/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

        response = stripe_webhook_view(request)

        self.assertEqual(response.status_code, 500)

    @patch("apps.payments.views.views.post_trip_creation")
    @patch("apps.payments.views.views._queue_booking_confirmations")
    @patch("apps.payments.views.views.create_trip_from_payment")
    def test_duplicate_success_skips_operational_side_effects_but_requeues_idempotent_confirmations(
        self, create_trip, queue_confirmations, post_creation
    ):
        trip = SimpleNamespace(
            id=77,
            passenger_email="test@example.invalid",
            is_guest_checkout=True,
        )
        create_trip.return_value = (trip, False)

        result = handle_payment_succeeded({
            "data": {
                "object": {
                    "id": "pi_duplicate",
                    "metadata": {"pending_payment_id": "12"},
                }
            }
        })

        self.assertIs(result, trip)
        queue_confirmations.assert_called_once_with(trip)
        post_creation.assert_not_called()

    def test_settled_amount_and_currency_must_match_authoritative_pending_price(self):
        pending = SimpleNamespace(
            price_breakdown={"total_cost": "123.45"},
            currency="GBP",
        )
        verify_payment_matches_pending(
            {
                "id": "pi_match",
                "amount_received": 12345,
                "currency": "gbp",
            },
            pending,
        )

        with self.assertRaisesRegex(Exception, "amount mismatch"):
            verify_payment_matches_pending(
                {
                    "id": "pi_wrong_amount",
                    "amount_received": 12344,
                    "currency": "gbp",
                },
                pending,
            )

        with self.assertRaisesRegex(Exception, "currency mismatch"):
            verify_payment_matches_pending(
                {
                    "id": "pi_wrong_currency",
                    "amount_received": 12345,
                    "currency": "usd",
                },
                pending,
            )

    def test_pending_payment_id_cannot_be_rebound_to_another_payment_intent(self):
        pending = PendingPayment.objects.create(
            payment_intent_id="pi_original",
            price_breakdown={"total_cost": 50},
            trip_data={},
            booking_details={},
            currency="GBP",
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        self.assertIsNone(
            get_pending_payment("pi_attacker", str(pending.id))
        )
        self.assertEqual(
            get_pending_payment("pi_original", str(pending.id)).id,
            pending.id,
        )
