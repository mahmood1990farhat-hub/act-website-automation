from django.test import SimpleTestCase
from django.urls import resolve

from apps.payments.urls import urlpatterns
from apps.payments.views.views import stripe_webhook_view


class PaymentURLTests(SimpleTestCase):
    def test_all_payment_url_callbacks_are_callable(self):
        self.assertTrue(urlpatterns)
        for url_pattern in urlpatterns:
            self.assertTrue(callable(url_pattern.callback))

    def test_stripe_webhook_resolves_to_expected_view(self):
        match = resolve("/api/payments/webhook/stripe/")

        self.assertIs(match.func, stripe_webhook_view)
