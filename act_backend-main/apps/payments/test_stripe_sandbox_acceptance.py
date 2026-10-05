import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from unittest.mock import patch

import stripe
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.payments.models import PendingPayment
from apps.trips.models import Trip
from apps.vehicle.models import VehicleType


@override_settings(
    STRIPE_WEBHOOK_SECRET="whsec_act_local_acceptance",
    CELERY_TASK_ALWAYS_EAGER=True,
)
class StripeSandboxFulfillmentAcceptanceTests(TestCase):
    """Opt-in integration test: requires STRIPE_SANDBOX_SECRET_KEY."""

    def setUp(self):
        key = os.environ.get("STRIPE_SANDBOX_SECRET_KEY", "")
        if not key:
            self.skipTest("STRIPE_SANDBOX_SECRET_KEY is not configured")
        stripe.api_key = key

        self.vehicle_type = VehicleType.objects.create(
            code="comfort",
            name_en="Comfort Class",
            name_ar="فئة الراحة",
            desc_en="Acceptance vehicle",
            desc_ar="مركبة اختبار",
            icon="vehicle_types/icons/acceptance.png",
            max_passengers_count=4,
            order=1,
        )

    def _pending(self):
        trip_date = timezone.localdate() + timedelta(days=2)
        return PendingPayment.objects.create(
            price_breakdown={
                "total_cost": "1.00",
                "base_trip_cost": "0.83",
                "regular_vat": "0.17",
                "airport_vat": "0.00",
                "min_adjustment": "0.00",
            },
            trip_data={
                "pickup_lat": 51.4700,
                "pickup_lng": -0.4543,
                "dropoff_lat": 51.5074,
                "dropoff_lng": -0.1278,
                "trip_date": trip_date.isoformat(),
                "trip_time": "14:00:00",
                "passengers_count": 1,
                "large_suitcase": 0,
                "small_suitcase": 0,
                "car_type": self.vehicle_type.id,
                "stop_points": [],
            },
            passenger_name="ACT Sandbox Passenger",
            passenger_email="sandbox-passenger@example.invalid",
            passenger_country_code="+44",
            passenger_phone="7700900000",
            booking_details={"language": "en"},
            currency="GBP",
            expires_at=timezone.now() + timedelta(minutes=30),
        )

    def _find_success_event(self, payment_intent_id):
        for _ in range(12):
            events = stripe.Event.list(
                type="payment_intent.succeeded",
                limit=20,
            )
            for event in events.auto_paging_iter():
                if event.data.object.id == payment_intent_id:
                    return event
            time.sleep(1)
        self.fail(f"Stripe sandbox success event not found for {payment_intent_id}")

    @patch("apps.payments.views.views.post_trip_creation")
    @patch("apps.payments.views.views._queue_booking_confirmations")
    def test_real_sandbox_success_event_creates_one_paid_trip(
        self, queue_confirmations, post_trip_creation
    ):
        pending = self._pending()

        intent = stripe.PaymentIntent.create(
            amount=100,
            currency="gbp",
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            payment_method="pm_card_visa",
            confirm=True,
            metadata={
                "pending_payment_id": str(pending.id),
                "act_acceptance": "website-payment-booking",
                "environment": "sandbox",
            },
            description="ACT Website Acceptance - successful sandbox payment",
        )
        self.assertEqual(intent.status, "succeeded")
        self.assertFalse(intent.livemode)
        # Always clean up the sandbox charge, even if a later webhook assertion fails.
        self.addCleanup(stripe.Refund.create, payment_intent=intent.id)

        pending.payment_intent_id = intent.id
        pending.save(update_fields=["payment_intent_id"])

        event = self._find_success_event(intent.id)
        self.assertFalse(event.livemode)

        # Use the real sandbox PaymentIntent and Stripe success-event ID,
        # while serializing only documented webhook fields ACT consumes.
        event_payload = {
            "id": event.id,
            "object": "event",
            "type": "payment_intent.succeeded",
            "livemode": False,
            "created": event.created,
            "data": {
                "object": {
                    "id": intent.id,
                    "object": "payment_intent",
                    "amount": intent.amount,
                    "amount_received": intent.amount_received,
                    "currency": intent.currency,
                    "metadata": intent.metadata.to_dict(),
                    "latest_charge": intent.latest_charge,
                }
            },
        }
        payload = json.dumps(event_payload, separators=(",", ":"))
        timestamp = int(time.time())
        secret = "whsec_act_local_acceptance"
        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        signature_header = f"t={timestamp},v1={signature}"

        response = self.client.post(
            "/api/payments/webhook/stripe/",
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature_header,
        )
        self.assertEqual(response.status_code, 200)

        trip = Trip.objects.get(stripe_payment_intent=intent.id)
        self.assertTrue(trip.is_paid)
        self.assertEqual(str(trip.cost), "1.00")
        self.assertEqual(trip.car_type.code, "comfort")
        self.assertFalse(PendingPayment.objects.filter(id=pending.id).exists())
        queue_confirmations.assert_called_once_with(trip)
        post_trip_creation.assert_called_once_with(trip)

        # Replay the exact same verified event: still one Trip and no repeated
        # operational post-processing. Confirmation task may be safely requeued.
        replay = self.client.post(
            "/api/payments/webhook/stripe/",
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature_header,
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(
            Trip.objects.filter(stripe_payment_intent=intent.id).count(),
            1,
        )
        self.assertEqual(post_trip_creation.call_count, 1)
        self.assertEqual(queue_confirmations.call_count, 2)
