"""Isolated review tests for preserving a failed ACT frontend release attempt."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
import retry_stripe_frontend as r

class RetrySafetyTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.old = root / 'failed-record'; self.old.mkdir(mode=0o700)
        self.new = root / 'retry-record'
        self.nginx = root / 'nginx'; self.nginx.mkdir()
        site = self.nginx / 'act.conf';site.write_bytes(b'synthetic old nginx configuration')
        self.site = self.nginx / 'site-link';self.site.symlink_to(site)
        self.dump = root / 'dump.pm2';self.dump.write_bytes(b'synthetic previous PM2 state')
        self.plan = {
            'activated':False,'frontend_source':r.FRONTEND_SOURCE,
            'backend_source':r.BACKEND_SOURCE,
            'old_nginx_sha256':r.sha(site.read_bytes()),
            'proposed_nginx_sha256':r.sha(b'synthetic proposed nginx'),
            'old_pm2_sha256':r.sha(self.dump.read_bytes()),
        }
        self.marker={'status':'RELEASE_PREPARATION_STARTED',
                     'payment_attempted':False,'backend_modified':False}
        fixtures={
          'RELEASE_PREPARATION_STARTED.json':json.dumps(self.marker).encode(),
          'nginx.before.conf':site.read_bytes(),
          'nginx.proposed.conf':b'synthetic proposed nginx',
          'pm2.before.json':self.dump.read_bytes(),
          'candidate.plan.json':json.dumps(self.plan).encode(),
        }
        for name,raw in fixtures.items():
            file = self.old / name;file.write_bytes(raw);file.chmod(0o600)
        self.patchers=[patch.object(r,'OLD_ATTEMPT',self.old),
                       patch.object(r,'RETRY_ATTEMPT',self.new),
                       patch.object(r,'SITE',self.site),
                       patch.object(r,'PM2_DUMP',self.dump),
                       patch.object(Path,'is_relative_to',return_value=True)]
        for p in self.patchers:p.start();self.addCleanup(p.stop)

    def inspect(self):
        return r.inspect_previous(uid=os.geteuid())

    def test_original_failure_state_accepted_without_writes(self):
        before={p.name:p.read_bytes() for p in self.old.iterdir()}
        self.assertIsNone(self.inspect())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.old.iterdir()})
        self.assertFalse(self.new.exists())

    def test_retry_record_exists_refuses_overwrite(self):
        self.new.mkdir()
        with self.assertRaisesRegex(r.Stop,'RETRY_RECORD_ALREADY_EXISTS'):
            self.inspect()

    def test_any_progress_after_pm2_start_prevents_retry(self):
        for name in r.MUST_NOT_EXIST:
            file=self.old/name
            with self.subTest(name=name):
                file.write_text('unexpected');file.chmod(0o600)
                with self.assertRaisesRegex(r.Stop,'PREVIOUS_ATTEMPT_PROGRESS_NOT_EXPECTED'):
                    self.inspect()
                file.unlink()

    def test_missing_saved_rollback_data_refuses(self):
        (self.old/'pm2.before.json').unlink()
        with self.assertRaises((r.Stop, FileNotFoundError)):
            self.inspect()

    def test_prior_record_symlink_refuses(self):
        file=self.old/'nginx.before.conf';file.unlink();file.symlink_to(self.dump)
        with self.assertRaisesRegex(r.Stop,'PREVIOUS_RECORD_FILE_LINK'):
            self.inspect()

    def test_prior_record_permissions_refuse(self):
        (self.old/'pm2.before.json').chmod(0o644)
        with self.assertRaisesRegex(r.Stop,'PREVIOUS_RECORD_FILE_NOT_PRIVATE'):
            self.inspect()

    def test_activated_or_wrong_preimage_refuses(self):
        for field,value in [('activated',True),('frontend_source','another'),('old_nginx_sha256','0'*64)]:
            with self.subTest(field=field):
                p={**self.plan,field:value}
                (self.old/'candidate.plan.json').write_text(json.dumps(p))
                with self.assertRaisesRegex(r.Stop,'PREVIOUS_FAILURE_PLAN_MISMATCH'):
                    self.inspect()
        (self.old/'candidate.plan.json').write_text(json.dumps(self.plan))

    def test_wrong_current_nginx_refuses(self):
        self.site.resolve().write_bytes(b'changed')
        with self.assertRaisesRegex(r.Stop,'LIVE_SITE_NOT_PREVIOUS_PREIMAGE'):
            self.inspect()

    def test_wrong_current_pm2_dump_refuses(self):
        self.dump.write_bytes(b'changed')
        with self.assertRaisesRegex(r.Stop,'PM2_SAVED_STATE_NOT_PREVIOUS_PREIMAGE'):
            self.inspect()

    def test_marker_mismatch_refuses(self):
        self.marker['backend_modified']=True
        (self.old/'RELEASE_PREPARATION_STARTED.json').write_text(json.dumps(self.marker))
        with self.assertRaisesRegex(r.Stop,'PREVIOUS_FAILURE_MARKER_MISMATCH'):
            self.inspect()

    def test_check_read_only_and_no_auto_deployment(self):
        fake=SimpleNamespace(RECORD=self.old,main=Mock(return_value=0))
        with patch.object(r.os,'geteuid',return_value=0),\
             patch.object(r,'inspect_previous') as inspect,\
             patch.object(r,'load_corrected_release',return_value=fake):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(r.main(['--check']),0)
        inspect.assert_called_once()
        fake.main.assert_called_once_with(['--check'])
        self.assertEqual(fake.RECORD,self.new)
        self.assertIn('RETRY_NOT_AUTHORISED',out.getvalue())

    def test_explicit_activate_separate_from_check(self):
        fake=SimpleNamespace(RECORD=self.old,main=Mock(return_value=0))
        with patch.object(r.os,'geteuid',return_value=0),\
             patch.object(r,'inspect_previous'),\
             patch.object(r,'load_corrected_release',return_value=fake):
            self.assertEqual(r.main(['--activate']),0)
        fake.main.assert_called_once_with(['--activate'])
        self.assertEqual(fake.RECORD,self.new)

    def test_unexpected_args_do_not_echo_keys(self):
        bad='pk_test_'+'Z'*32
        out=io.StringIO()
        with contextlib.redirect_stderr(out):
            self.assertEqual(r.main(['--activate='+bad]),1)
        self.assertNotIn(bad,out.getvalue())
        self.assertIn('ONLY_CHECK_OR_SEPARATELY_APPROVED_RETRY_ACCEPTED',out.getvalue())

    def test_root_required_before_check(self):
        with patch.object(r.os,'geteuid',return_value=1000),patch.object(r,'inspect_previous') as inspect:
            out=io.StringIO()
            with contextlib.redirect_stderr(out):
                self.assertEqual(r.main(['--check']),1)
        self.assertIn('ROOT_VPS_REQUIRED',out.getvalue())
        inspect.assert_not_called()

    def test_wrong_original_script_record_marker_refused(self):
        fake=SimpleNamespace(RECORD=Path('/incorrect-record'),main=Mock())
        with patch.object(r.os,'geteuid',return_value=0),patch.object(r,'inspect_previous'),\
             patch.object(r,'load_corrected_release',return_value=fake):
            out=io.StringIO()
            with contextlib.redirect_stderr(out):
                self.assertEqual(r.main(['--check']),1)
        self.assertIn('ORIGINAL_ACTIVATION_RECORD_PATH_CHANGED',out.getvalue())
        fake.main.assert_not_called()

if __name__ == '__main__':unittest.main()