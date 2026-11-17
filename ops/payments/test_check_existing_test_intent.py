"""Isolated, synthetic read-only Stripe compatibility checks; no provider traffic."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch, Mock

RECOVERY = ModuleType('replace_expired_test_key')


class Refusal(Exception):
    pass


def require(condition, code):
    if not condition:
        raise Refusal(code)


RECOVERY.Refusal = Refusal
RECOVERY.require = require
RECOVERY.ACCOUNT = 'acct_1RDnQjBxjYEaMc5N'
RECOVERY.read_env = Mock(return_value=SimpleNamespace(data=b'private fixture'))
RECOVERY.service_snapshot = Mock(return_value={'key_source': 'systemd-shared-env'})
RECOVERY.key_span = Mock(return_value=(0, 0, 'sk_test_' + 'S' * 32))
RECOVERY.stripe_response = Mock()
sys.modules[RECOVERY.__name__] = RECOVERY

SOURCE = Path(__file__).with_name('check_existing_test_intent.py')
spec = importlib.util.spec_from_file_location('act_test_intent_diagnostic', SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
INTENT = 'pi_' + 'A' * 25
CLIENT_SECRET = INTENT + '_secret_' + 'C' * 28
PUBLIC_KEY = 'pk_test_' + 'P' * 32
SECRET_KEY = 'sk_test_' + 'S' * 32


class ReadOnlyCheckTests(unittest.TestCase):
    def setUp(self):
        for obj in (RECOVERY.read_env, RECOVERY.service_snapshot, RECOVERY.key_span, RECOVERY.stripe_response):
            obj.reset_mock()
        RECOVERY.read_env.return_value = SimpleNamespace(data=b'private fixture')
        RECOVERY.key_span.return_value = (0, 0, SECRET_KEY)
        self.root = patch.object(subject.os, 'geteuid', return_value=0)
        self.key = patch.object(subject, 'captured_public_key', return_value=PUBLIC_KEY)
        self.root.start()
        self.key.start()
        self.responses = [
            (200, {'id': RECOVERY.ACCOUNT}),
            (200, {'id': INTENT, 'livemode': False, 'status': 'requires_payment_method',
                   'amount_received': 0, 'payment_method': None, 'client_secret': CLIENT_SECRET}),
            (200, {'id': INTENT, 'livemode': False, 'status': 'requires_payment_method'}),
        ]
        RECOVERY.stripe_response.side_effect = lambda *_: self.responses.pop(0)

    def tearDown(self):
        self.root.stop()
        self.key.stop()

    def test_success_is_only_gets_and_never_prints_keys(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = subject.main(['--payment-intent-id', INTENT])
        self.assertEqual(code, 0)
        self.assertIn('CAPTURED_PUBLIC_KEY_CAN_READ_EXISTING_TEST_INTENT', out.getvalue())
        combined = out.getvalue() + err.getvalue()
        for secret in (PUBLIC_KEY, SECRET_KEY, CLIENT_SECRET, INTENT):
            self.assertNotIn(secret, combined)
        calls = RECOVERY.stripe_response.call_args_list
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0].args, ('/v1/account', SECRET_KEY))
        self.assertEqual(calls[1].args, ('/v1/payment_intents/' + INTENT, SECRET_KEY))
        self.assertEqual(calls[2].args, ('/v1/payment_intents/' + INTENT + '?client_secret=' + CLIENT_SECRET, PUBLIC_KEY))
        self.assertTrue(all(path.startswith('/v1/') for path, _ in [call.args for call in calls]))
        RECOVERY.service_snapshot.assert_called_once()

    def test_missing_under_public_key_is_explicit_not_assumed_cause(self):
        self.responses[-1] = (404, {'error': {'code': 'resource_missing',
                                             'message': 'Sensitive provider message'}})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = subject.main(['--payment-intent-id', INTENT])
        self.assertEqual(code, 2)
        self.assertIn('CAPTURED_PUBLIC_KEY_CANNOT_FIND_EXISTING_TEST_INTENT', out.getvalue())
        self.assertNotIn('Sensitive provider message', out.getvalue())

    def test_invalid_public_key_is_classified_without_echo(self):
        self.responses[-1] = (401, {'error': {'code': 'invalid_api_key'}})
        self.assertEqual(subject.check(INTENT), 'CAPTURED_PUBLIC_KEY_REJECTED')

    def test_existing_intent_must_still_be_unpaid(self):
        self.responses[1] = (
            200, {'id': INTENT, 'livemode': False, 'status': 'succeeded',
                  'payment_method': 'pm_test', 'amount_received': 544, 'client_secret': CLIENT_SECRET})
        with self.assertRaisesRegex(Refusal, 'INTENT_STATE_CHANGED_STOP_BEFORE_DIAGNOSIS'):
            subject.check(INTENT)
        self.assertEqual(RECOVERY.stripe_response.call_count, 2)

    def test_account_mismatch_blocks_intent_access(self):
        self.responses[0] = (200, {'id': 'acct_unrelated'})
        with self.assertRaisesRegex(Refusal, 'BACKEND_TEST_ACCOUNT_NOT_VERIFIED'):
            subject.check(INTENT)
        self.assertEqual(RECOVERY.stripe_response.call_count, 1)

    def test_malformed_client_secret_blocks_public_request(self):
        self.responses[1] = (
            200, {'id': INTENT, 'livemode': False, 'status': 'requires_payment_method',
                  'amount_received': 0, 'payment_method': None, 'client_secret': 'not_secret'})
        with self.assertRaisesRegex(Refusal, 'CLIENT_SECRET_NOT_VALID_FOR_INTENT'):
            subject.check(INTENT)
        self.assertEqual(RECOVERY.stripe_response.call_count, 2)

    def test_invalid_intent_or_non_root_blocks_all_network(self):
        for candidate in ['sk_test_' + 'Z'*32, 'pi_invalid; rm -rf /', '']:
            with self.subTest(candidate=candidate), self.assertRaises(Refusal):
                subject.check(candidate)
        RECOVERY.stripe_response.assert_not_called()
        with patch.object(subject.os, 'geteuid', return_value=1000), self.assertRaisesRegex(
                Refusal, 'ROOT_READ_ONLY_TERMINAL_REQUIRED'):
            subject.check(INTENT)
        RECOVERY.stripe_response.assert_not_called()

    def test_argparse_never_echoes_accidental_key(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = subject.main(['--invalid-arg=' + SECRET_KEY])
        self.assertEqual(result, 1)
        self.assertIn('EXPECTED_ONLY_PAYMENT_INTENT_ID_NO_KEYS', err.getvalue())
        self.assertNotIn(SECRET_KEY, err.getvalue() + out.getvalue())
        RECOVERY.stripe_response.assert_not_called()

    def test_captured_public_receipt_and_permissions(self):
        self.key.stop()
        self.key = patch.object(subject, 'captured_public_key', wraps=subject.captured_public_key)
        self.key.start()
        with tempfile.TemporaryDirectory() as base:
            receipt = Path(base) / 'public.json'
            receipt.write_text(json.dumps({'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY': PUBLIC_KEY}))
            receipt.chmod(0o600)
            with patch.object(subject, 'FRONTEND_PUBLIC_ENV', receipt):
                self.assertEqual(subject.captured_public_key(), PUBLIC_KEY)
                receipt.chmod(0o644)
                with self.assertRaisesRegex(Refusal, 'FRONTEND_RECEIPT_NOT_ROOT_PRIVATE'):
                    subject.captured_public_key()
                receipt.chmod(0o600)
                receipt.write_text(json.dumps({'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY': 'pk_live_not_allowed'}))
                with self.assertRaisesRegex(Refusal, 'CAPTURED_PUBLIC_KEY_NOT_TEST_MODE'):
                    subject.captured_public_key()

    def test_unknown_provider_reply_does_not_expose_raw_payload(self):
        self.responses[-1] = (400, {'error': {'code': 'unknown', 'message': CLIENT_SECRET}})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(subject.main(['--payment-intent-id', INTENT]), 2)
        self.assertIn('PUBLIC_READ_NOT_VERIFIED', out.getvalue())
        self.assertNotIn(CLIENT_SECRET, out.getvalue())


if __name__ == '__main__':
    unittest.main()
