"""Offline, synthetic safety checks. No Stripe/API/network/systemd, PM2 or VPS writes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
import os

spec = importlib.util.spec_from_file_location('prepare_frontend', Path(__file__).with_name('prepare_stripe_frontend_candidate.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
OLD='pk_test_'+'A'*32
NEW='pk_test_'+'B'*32
INTENT_SECRET=p.INTENT+'_secret_'+'C'*32


class BuildSafetyTests(unittest.TestCase):
    def test_status_mode_has_no_key_or_config_mutation(self):
        with patch.object(p, 'local_state', return_value={'active_public':{'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY':OLD}}), \
             patch.object(p, 'stage') as stage, patch.object(p, 'read_verified_helper') as helper:
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(p.main(['--check']),0)
            self.assertIn('NO_CHANGES',stream.getvalue())
            stage.assert_not_called();helper.assert_not_called()

    def test_unknown_argument_does_not_echo_pasted_key(self):
        stream=io.StringIO()
        with contextlib.redirect_stderr(stream):
            self.assertEqual(p.main(['--prepare='+NEW]),1)
        self.assertNotIn(NEW,stream.getvalue())
        self.assertIn('EXPECTED_ONLY_CHECK_OR_PREPARE_NO_KEY_ARGUMENT',stream.getvalue())

    def test_invalid_candidate_refused_before_provider_call(self):
        h=SimpleNamespace(read_env=Mock(),stripe_response=Mock())
        for invalid in (OLD,'pk_live_'+ 'A'*32,NEW+'!', 'pk_test_short'):
            with self.subTest(invalid=invalid[:14]),self.assertRaises(p.Stop):
                p.verify_candidate(invalid,OLD,h)
        h.read_env.assert_not_called();h.stripe_response.assert_not_called()

    def helper(self,response=None):
        if response is None:
            response=[(200, {'id':p.ACCOUNT}),
                      (200,{'id':p.INTENT,'livemode':False,'status':'requires_payment_method',
                            'payment_method':None,'amount_received':0,'client_secret':INTENT_SECRET}),
                      (200, {'id':p.INTENT,'livemode':False})]
        return SimpleNamespace(
            read_env=Mock(return_value=SimpleNamespace(data=b'fake-secret')),
            service_snapshot=Mock(),key_span=Mock(return_value=(0,0,'sk_test_'+'S'*32)),
            stripe_response=Mock(side_effect=response))

    def test_candidate_verification_existing_intent_read_only(self):
        h=self.helper()
        p.verify_candidate(NEW,OLD,h)
        self.assertEqual(h.stripe_response.call_count,3)
        self.assertEqual(h.stripe_response.call_args_list[0].args[0],'/v1/account')
        self.assertTrue(h.stripe_response.call_args_list[2].args[0].startswith('/v1/payment_intents/'+p.INTENT+'?client_secret='))
        self.assertEqual(h.stripe_response.call_args_list[2].args[1],NEW)

    def test_public_account_rejection_blocks_build(self):
        h=self.helper(response=[(200,{'id':p.ACCOUNT}),
            (200,{'id':p.INTENT,'livemode':False,'status':'requires_payment_method',
                  'payment_method':None,'amount_received':0,'client_secret':INTENT_SECRET}),
            (401,{'error':{'code':'api_key_expired','message':'raw potentially sensitive value'}})])
        with self.assertRaisesRegex(p.Stop,'REPLACEMENT_TEST_PUBLIC_KEY_NOT_VERIFIED'):
            p.verify_candidate(NEW,OLD,h)

    def test_charged_or_mismatched_intent_blocks_build(self):
        for intent in ({'id':p.INTENT,'livemode':False,'status':'succeeded','payment_method':'pm','amount_received':544},
                       {'id':'pi_other','livemode':False,'status':'requires_payment_method','payment_method':None,'amount_received':0},
                       {'id':p.INTENT,'livemode':True,'status':'requires_payment_method','payment_method':None,'amount_received':0}):
            h=self.helper(response=[(200,{'id':p.ACCOUNT}),(200,intent)])
            with self.subTest(intent=intent),self.assertRaisesRegex(p.Stop,'EXISTING_TEST_INTENT_NOT_UNPAID'):
                p.verify_candidate(NEW,OLD,h)
            self.assertEqual(h.stripe_response.call_count,2)

    def test_backend_account_guard_blocks_intent(self):
        h=self.helper(response=[(200, {'id':'acct_unauthorized'})])
        with self.assertRaisesRegex(p.Stop,'BACKEND_STRIPE_ACCOUNT_NOT_VERIFIED'):
            p.verify_candidate(NEW, OLD,h)
        self.assertEqual(h.stripe_response.call_count,1)

    def test_js_bundle_key_detection(self):
        with TemporaryDirectory() as td:
            root=Path(td); f=root/'.next/static/chunks/main.js';f.parent.mkdir(parents=True)
            f.write_bytes(('const key="'+OLD+'";').encode())
            self.assertEqual(p.js_keys(root),{OLD.encode()})
            f.write_bytes(('const a="'+OLD+'";const b="'+NEW+'";').encode())
            self.assertEqual(p.js_keys(root),{OLD.encode(),NEW.encode()})
            f.unlink();f.symlink_to('/etc/passwd')
            with self.assertRaisesRegex(p.Stop,'UNEXPECTED_COMPILED_JS_LINK'):
                p.js_keys(root)

    def test_private_receipt_and_expected_origin(self):
        with TemporaryDirectory() as td:
            x=Path(td)/'frontend-public-environment.json'
            value={'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY':OLD,
                   'NEXT_PUBLIC_API_BASE_URL':'https://airportandcitytransfer.com'}
            x.write_text(json.dumps(value));x.chmod(0o600)
            with patch.object(p,'RECEIPT',x):
                self.assertEqual(p.receipt(),value)
                x.chmod(0o644)
                with self.assertRaisesRegex(p.Stop,'PUBLIC_CONFIGURATION_RECEIPT_NOT_PRIVATE'):
                    p.receipt()
                x.chmod(0o600);value['NEXT_PUBLIC_API_BASE_URL']='https://unrelated.example'
                x.write_text(json.dumps(value))
                with self.assertRaisesRegex(p.Stop,'PUBLIC_API_BASE_DRIFT'):
                    p.receipt()

    def test_no_candidate_overwrite_even_when_prepare_invoked(self):
        with TemporaryDirectory() as td:
            candidate=Path(td)/'candidate';candidate.mkdir()
            with patch.object(p,'CANDIDATE',candidate),patch.object(p,'NEW_ASSETS',Path(td)/'new-assets'), \
                 patch.object(p,'RECORD',Path(td)/'record'),patch.object(p,'command') as cmd:
                with self.assertRaisesRegex(p.Stop,'CANDIDATE_ALREADY_EXISTS_STOP_NO_OVERWRITE'):
                    p.stage(NEW,{})
                cmd.assert_not_called()

    def test_asset_union_preserves_old_and_rejects_collision(self):
        with TemporaryDirectory() as td:
            root=Path(td); old=root/'old';new=root/'release/.next/static';dest=root/'new-assets'
            old.mkdir();new.mkdir(parents=True)
            (old/'legacy.js').write_text('old');(new/'current.js').write_text('new')
            with patch.object(p,'OLD_ASSETS',old),patch.object(p,'CANDIDATE',root/'release'),patch.object(p,'NEW_ASSETS',dest):
                p.copy_asset_union()
                self.assertEqual((dest/'legacy.js').read_text(),'old')
                self.assertEqual((dest/'current.js').read_text(),'new')
                self.assertEqual(dest.stat().st_mode & 0o777,0o755)
                self.assertEqual((dest/'current.js').stat().st_mode & 0o777,0o644)
                (new/'legacy.js').write_text('different')
                with self.assertRaisesRegex(FileExistsError,'File exists'):
                    p.copy_asset_union()

    def test_local_state_declines_drift_and_no_stage(self):
        with patch.object(p,'local_state',side_effect=p.Stop('ACTIVE_FRONTEND_PROCESS_DRIFT')), \
             patch.object(p,'stage') as stage:
            err=io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(p.main(['--prepare']),1)
            self.assertIn('ACTIVE_FRONTEND_PROCESS_DRIFT',err.getvalue())
            stage.assert_not_called()


if __name__ == '__main__':
    unittest.main()
