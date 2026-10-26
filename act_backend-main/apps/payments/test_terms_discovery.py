"""New public terms contract and parity with existing pre-payment capture only.
Synthetic documents/records. No PDFs rendered or real provider/network requests.
"""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import socket
from unittest.mock import patch

from django.test import SimpleTestCase, TransactionTestCase, RequestFactory, override_settings

from apps.payments import test_booking_contracts as fixture
from apps.payments.models import BookingTermsAcceptance
from apps.payments.booking_contracts import ContractConflict, capture_checkout_terms
from apps.payments.terms_discovery import checkout_terms_view

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


@override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=True, ACT_BOOKING_TERMS_RELEASE=fixture.RELEASE)
class TermsDiscoveryTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(patch('apps.payments.terms_discovery.timezone.now', return_value=NOW))
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('Discovery must not use networking')))

    def get(self, query='locale=en', method='get'):
        request = getattr(RequestFactory(), method)('/api/payments/checkout-terms/?'+query)
        return checkout_terms_view(request)

    def data(self, response):
        import json
        return json.loads(response.content)

    def test_default_disabled_never_exposes_a_draft(self):
        with override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=False, ACT_BOOKING_TERMS_RELEASE={'text': 'PRIVATE DRAFT'}):
            self.assertEqual(self.data(self.get()), {'schema': 1, 'enabled': False})

    def test_exact_public_fields_and_no_store(self):
        response = self.get(); data = self.data(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(set(data), {'schema', 'enabled', 'terms_version', 'terms_sha256', 'locale', 'text', 'document_url', 'pdf_sha256', 'effective_at'})
        self.assertEqual(data['text'], fixture.TEXT)
        self.assertEqual(data['terms_sha256'], fixture.HASH)
        self.assertEqual(data['document_url'], fixture.RELEASE['locales']['en']['url'])

    def test_only_public_allowlist_exposed(self):
        release = deepcopy(fixture.RELEASE)
        release['internal_notes'] = 'NOT PUBLIC'
        release['locales']['en']['secret'] = 'NOT PUBLIC'
        with override_settings(ACT_BOOKING_TERMS_RELEASE=release):
            self.assertNotIn(b'NOT PUBLIC', self.get().content)

    def test_missing_unpublished_and_invalid_release_are_closed(self):
        for release in (None, {}, 'invalid', {**fixture.RELEASE, 'published': False},
                        {**fixture.RELEASE, 'published': 1}, {**fixture.RELEASE, 'policy_version': 'invented'}):
            with self.subTest(release=release), override_settings(ACT_BOOKING_TERMS_RELEASE=release):
                self.assertEqual(self.get().status_code, 503)

    def test_future_naive_missing_and_bad_effective_dates(self):
        for value in ('2099-01-01T00:00:00Z', '2026-01-01T00:00:00', None, 'broken'):
            with self.subTest(value=value), override_settings(ACT_BOOKING_TERMS_RELEASE={**fixture.RELEASE, 'effective_at': value}):
                response = self.get()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(self.data(response), {'schema': 1, 'error': 'terms_unavailable'})

    def test_missing_locale_never_falls_back_to_english(self):
        self.assertEqual(self.get('locale=ar').status_code, 503)
        for query in ('', 'locale=xx', 'locale=EN', 'locale=en&locale=ar', 'locale=en&terms_version=other'):
            with self.subTest(query=query): self.assertEqual(self.get(query).status_code, 400)

    def test_strict_boolean_activation(self):
        for value in ('true', 1, None):
            with override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=value):
                self.assertEqual(self.get().status_code, 503)

    def test_changed_text_without_new_hash_is_not_served(self):
        release = deepcopy(fixture.RELEASE); release['locales']['en']['text'] += 'changed'
        with override_settings(ACT_BOOKING_TERMS_RELEASE=release):
            self.assertEqual(self.get().status_code, 503)

    def test_pdf_path_and_hash_reject_external_or_malformed_values(self):
        for key, value in (('url', 'https://elsewhere.invalid/terms.pdf'), ('url', '//evil.invalid/a.pdf'),
                           ('url', '/documents/../secret.pdf'), ('url', '/documents/en//v1.pdf'),
                           ('pdf_sha256', ''), ('pdf_sha256', True)):
            release = deepcopy(fixture.RELEASE); release['locales']['en'][key] = value
            with self.subTest(key=key,value=value), override_settings(ACT_BOOKING_TERMS_RELEASE=release):
                self.assertEqual(self.get().status_code, 503)

    def test_version_text_and_locales_shape_are_bounded(self):
        for release in ({**fixture.RELEASE, 'terms_version': ''}, {**fixture.RELEASE, 'terms_version': 'bad\nversion'},
                        {**fixture.RELEASE, 'locales': []}, {**fixture.RELEASE, 'locales': {'en': {'text': ' '*3}}}):
            with override_settings(ACT_BOOKING_TERMS_RELEASE=release): self.assertEqual(self.get().status_code, 503)

    def test_translated_content_is_returned_exactly_not_generated(self):
        release = deepcopy(fixture.RELEASE)
        text = 'نص اصطناعي للاختبار فقط — ليس سياسة منشورة'
        release['locales']['ar'] = {**release['locales']['en'], 'text': text,
            'sha256': hashlib.sha256(text.encode()).hexdigest(), 'url': '/documents/ar/test-only-v1.pdf'}
        with override_settings(ACT_BOOKING_TERMS_RELEASE=release):
            data = self.data(self.get('locale=ar'))
            self.assertEqual((data['locale'], data['text']), ('ar', text))

    def test_non_get_methods_cannot_record_consent(self):
        for method in ('post','put','delete','patch'):
            with self.subTest(method=method): self.assertEqual(self.get(method=method).status_code, 405)

    def test_json_content_cannot_be_used_as_html_response(self):
        release = deepcopy(fixture.RELEASE); text = '<script>synthetic only</script>'
        release['locales']['en'].update(text=text, sha256=hashlib.sha256(text.encode()).hexdigest())
        with override_settings(ACT_BOOKING_TERMS_RELEASE=release):
            response=self.get(); self.assertTrue(response['Content-Type'].startswith('application/json'))
            self.assertEqual(self.data(response)['text'], text)


@override_settings(ACT_BOOKING_TERMS_CHECKOUT_ENABLED=True, ACT_BOOKING_TERMS_RELEASE=fixture.RELEASE)
class TermsDiscoveryCaptureTests(TransactionTestCase):
    def setUp(self):
        # Reuse fixtures, NOT previously completed test methods.
        fixture.BookingContractStorageTests.setUp(self)
        self.enterContext(patch('apps.payments.terms_discovery.timezone.now', return_value=self.now))

    def read_ack(self):
        import json
        data=json.loads(checkout_terms_view(RequestFactory().get('/?locale=en')).content)
        ack={'accepted': True, 'terms_version': data['terms_version'],
             'terms_sha256': data['terms_sha256'], 'locale': data['locale']}
        return data, ack

    def capture(self, ack):
        return capture_checkout_terms(self.pending.pk, acknowledgement=ack, locale='en',
            received_at=self.now, confirmed_pickup_at=self.pickup)

    def test_displayed_document_matches_durable_acceptance(self):
        data, ack=self.read_ack()
        self.assertEqual(BookingTermsAcceptance.objects.count(), 0)
        record=self.capture(ack)
        self.assertEqual(record.snapshot['terms_text'], data['text'])
        self.assertEqual(record.snapshot['terms_sha256'], data['terms_sha256'])
        self.assertEqual(record.snapshot['document_url'], data['document_url'])
        self.assertEqual(record.snapshot['pdf_sha256'], data['pdf_sha256'])

    def test_release_change_after_viewing_is_rejected_before_acceptance(self):
        _, ack=self.read_ack(); release=deepcopy(fixture.RELEASE)
        release['terms_version']='test-only-v2'
        with override_settings(ACT_BOOKING_TERMS_RELEASE=release), self.assertRaises(ContractConflict):
            self.capture(ack)
        self.assertEqual(BookingTermsAcceptance.objects.count(), 0)

    def test_viewing_does_not_satisfy_explicit_acceptance(self):
        _, ack=self.read_ack()
        with self.assertRaises(ContractConflict): self.capture({**ack,'accepted':False})
        self.assertEqual(BookingTermsAcceptance.objects.count(), 0)
