from unittest.mock import patch

from django.test import SimpleTestCase

from apps.payments.views.views import extract_card_details


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
