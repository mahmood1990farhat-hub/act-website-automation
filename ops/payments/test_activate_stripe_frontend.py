"""Isolated synthetic safety tests. No VPS, Stripe, Nginx, PM2 or customer traffic."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import activate_stripe_frontend as m

OLD = 'pk_test_' + 'O'*32
NEW = 'pk_test_' + 'N'*32
OLD_HTML = b'<html>oldbuild<script src="/_next/static/chunks/old.js"></script></html>'
NEW_HTML = b'<html>newbuild<script src="/_next/static/chunks/new.js"></script></html>'


class Safety(unittest.TestCase):
    def test_safe_parser_never_echoes_arguments(self):
        with self.assertRaisesRegex(m.Stop, 'ONLY_CHECK_OR_APPROVED_ACTIVATE_ACCEPTED'):
            m.SafeParser().parse_args(['--unexpected=sk_test_1234567890ABCDEF'])

    def test_checkout_html_build_identity(self):
        old=SimpleNamespace(html_assets=lambda s: {'/_next/static/chunks/new.js'})
        a=m.page_assets(old, NEW_HTML, build_id='newbuild', other_id='oldbuild')
        self.assertEqual(a,{'/_next/static/chunks/new.js'})
        with self.assertRaisesRegex(m.Stop,'FRONTEND_BUILD_ID_MISMATCH'):
            m.page_assets(old,OLD_HTML,build_id='newbuild',other_id='oldbuild')

    def test_html_missing_js_refused(self):
        old=SimpleNamespace(html_assets=lambda s: set())
        with self.assertRaisesRegex(m.Stop,'FRONTEND_HTML_NO_STATIC_ASSETS'):
            m.page_assets(old,NEW_HTML,build_id='newbuild',other_id='oldbuild')

    def test_http_200_is_required(self):
        with patch.object(m,'command',return_value=b'failed\n404'):
            with self.assertRaisesRegex(m.Stop,'FRONTEND_HTTP_NOT_200'):
                m.http('http://127.0.0.1:3005/en',direct=True)

    def test_http_direct_host_headers_and_read_only_get(self):
        with patch.object(m,'command',return_value=b'<html/>\n200') as call:
            self.assertEqual(m.http('http://127.0.0.1:3005/en',direct=True),b'<html/>')
        args=call.call_args.args[0]
        self.assertIn('Host: airportandcitytransfer.com',args)
        self.assertIn('http://127.0.0.1:3005/en',args)
        self.assertNotIn('-X',args)

    def test_private_write_is_exclusive(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/'receipt.json'
            m.write_new(f,b'original')
            self.assertEqual(f.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):m.write_new(f,b'replace')
            self.assertEqual(f.read_bytes(),b'original')

    def test_journal_no_payment_claim(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            m.journal(p,'TEST_STATE')
            obj=json.loads((p/'TEST_STATE.json').read_bytes())
            self.assertEqual(obj['backend_modified'],False)
            self.assertEqual(obj['payment_attempted'],False)
            with self.assertRaises(FileExistsError):m.journal(p,'TEST_STATE')

    def test_private_record_has_both_nginx_configs_before_validation(self):
        # Real exclusive writes into a private temp dir. nginx/systemctl/PM2
        # are not executed. The old script failed this regression on rollback.
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)
            record=base/'activation-record'
            master=base/'nginx.conf';master.write_bytes(b'synthetic master')
            site=base/'sites-enabled/site.conf'
            site.parent.mkdir();site.write_bytes(b'original site')
            seen=[]
            def validation_master(master_bytes,entries,cfg):
                self.assertTrue(cfg.is_file(), 'nginx site include must exist before nginx -t')
                self.assertEqual(cfg.read_bytes(), b'new-site' if 'proposed' in cfg.name else b'old-site')
                seen.append(cfg.name)
                return b'synthetic validation master'
            prior=SimpleNamespace(MASTER=master,SITE=site,validation_master=validation_master)
            obj=m.Release(None,prior,object())
            obj.original=b'old-site';obj.proposed=b'new-site';obj.original_dump=b'old-pm2'
            obj.plan={'source_sha':'a'*40,'backend_sha':'b'*40,
                      'old_build_id':'previousbuild','new_build_id':'replacementbuild'}
            with patch.object(m,'RECORD',record),patch.object(m,'command',return_value=b'') as cli:
                obj.private_record()
            self.assertEqual(seen,['nginx.proposed.conf','nginx.rollback.conf'])
            self.assertEqual((record/'nginx.proposed.conf').read_bytes(),b'new-site')
            self.assertEqual((record/'nginx.rollback.conf').read_bytes(),b'old-site')
            self.assertTrue((record/'BOTH_NGINX_CONFIGS_VALIDATED.json').is_file())
            self.assertEqual(cli.call_count,2)
            self.assertTrue(all(call.args[0][0]=='/usr/sbin/nginx' for call in cli.call_args_list))
            # Do not allow a second attempt to overwrite the preserved record.
            with patch.object(m,'RECORD',record), self.assertRaises(FileExistsError):
                obj.private_record()

    def test_candidate_identity_uses_prior_removal_marker(self):
        with tempfile.TemporaryDirectory() as root:
            stage=SimpleNamespace(CANDIDATE=Path(root),
                js_keys=lambda path:{NEW.encode()})
            (Path(root)/'node_modules/next/dist/bin').mkdir(parents=True)
            (Path(root)/'node_modules/next/dist/bin/next').write_text('test')
            prior=SimpleNamespace(NODE=Path('/fake/node'),POLICY={'autorestart':True})
            obj=m.Release(None,prior,stage)
            obj.baseline={'active_public':{'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY':OLD}}
            obj.record=Path('/root/private/new-switch')
            c=obj.candidate_config()
            self.assertEqual(c['env']['ACT_TRACKING_ACTIVATION'],str(obj.record))
            self.assertEqual(c['env']['ACT_STRIPE_TEST_KEY_RELEASE'],str(obj.record))
            self.assertEqual(c['env']['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'],NEW)
            self.assertEqual(c['args'],['start','--hostname','127.0.0.1','--port','3005'])
            self.assertEqual(c['cwd'],root)

    def fake_rollback(self,root):
        root=Path(root)
        site=root/'site.conf';site.write_bytes(b'new-site')
        dump=root/'dump.pm2';dump.write_bytes(b'new-dump')
        pm2=root/'pm2';pm2.mkdir();(pm2/'pm2.pid').write_text('9999')
        prev=SimpleNamespace(DUMP=dump,PM2_HOME=pm2,NODE=Path('/node'),PM2_ROOT=Path('/pm2'),
            PM2_REMOVE='node script',IDENTITY=('name',),act_env=lambda:{},
            atomic_file=lambda path,data,pre: path.write_bytes(data),
        )
        stage=SimpleNamespace(CANDIDATE=root/'candidate',OLD_ASSETS=root/'old-assets')
        obj=m.Release(None,prev,stage)
        obj.record=root;obj.started=True;obj.complete=False
        obj.site=site;obj.original=b'old-site';obj.proposed=b'new-site'
        obj.original_dump=b'old-dump';obj.new_dump=b'new-dump';obj.saved=True
        obj.reloaded=True;obj.ids=[{'name':'A'}]*4
        obj.plan={'old_build_id':'old','new_build_id':'new'}
        obj.old_assets={'/_next/static/chunks/old.js'}
        obj.guard=lambda expected:True
        return obj

    def test_rollback_restores_only_preimages_and_removes_named_candidate(self):
        with tempfile.TemporaryDirectory() as root:
            obj=self.fake_rollback(root)
            calls=[]
            def command(args,**kwargs):
                calls.append((args,kwargs))
                return b''
            with patch.object(m,'command',side_effect=command),\
                 patch.object(m,'process_rows',return_value=[{}, {}, {}, {}]),\
                 patch.object(m,'verify_public') as pub,\
                 patch.object(m,'journal'):
                with contextlib.redirect_stdout(io.StringIO()):
                    obj.rollback()
            self.assertEqual(obj.site.read_bytes(),b'old-site')
            self.assertEqual(obj.prior.DUMP.read_bytes(),b'old-dump')
            encoded=json.loads([kw['data'] for args,kw in calls if args[-2]=='node script'][0])
            self.assertEqual(encoded['name'],m.NAME)
            self.assertEqual(encoded['activation_nonce'],str(obj.record))
            self.assertEqual(encoded['cwd'],str(obj.stage.CANDIDATE))
            self.assertEqual(encoded['allow_absent'],True)
            self.assertEqual(encoded['retained'],obj.ids)
            pub.assert_called_once()

    def test_rollback_refuses_unrecognised_nginx_before_pm2(self):
        with tempfile.TemporaryDirectory() as root:
            obj=self.fake_rollback(root)
            obj.site.write_bytes(b'external-unknown-update')
            with patch.object(m,'command') as cli,patch.object(m,'journal'):
                with self.assertRaisesRegex(m.Stop,'ROLLBACK_NGINX_UNRECOGNISED'):
                    obj.rollback()
            cli.assert_not_called()
            self.assertEqual(obj.prior.DUMP.read_bytes(),b'new-dump')

    def test_rollback_refuses_unrecognised_pm2_dump(self):
        with tempfile.TemporaryDirectory() as root:
            obj=self.fake_rollback(root)
            obj.prior.DUMP.write_bytes(b'external-pm2-edit')
            with patch.object(m,'command',return_value=b''),patch.object(m,'journal'):
                with self.assertRaisesRegex(m.Stop,'ROLLBACK_PM2_DUMP_UNRECOGNISED'):
                    obj.rollback()
            self.assertEqual(obj.prior.DUMP.read_bytes(),b'external-pm2-edit')

    def test_rollback_before_any_process_start_is_noop(self):
        with tempfile.TemporaryDirectory() as root:
            obj=self.fake_rollback(root);obj.started=False
            with patch.object(m,'command') as cli:
                obj.rollback()
            cli.assert_not_called()
            self.assertEqual(obj.site.read_bytes(),b'new-site')

    def test_check_mode_requires_root_and_preserves_runtime(self):
        checker=SimpleNamespace(check=Mock())
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m,'load',side_effect=[checker,object()]),\
             patch('builtins.input') as prompt:
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main(['--check']),0)
            self.assertIn('NO_CHANGES',out.getvalue())
            checker.check.assert_called_once()
            prompt.assert_not_called()

    def test_nonroot_refuses_all(self):
        with patch.object(m.os,'geteuid',return_value=1000),\
             patch.object(m,'load') as loader,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--check']),1)
        loader.assert_not_called()

    def test_activation_requires_tty(self):
        checker=SimpleNamespace(check=Mock())
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m,'load',side_effect=[checker,object()]),\
             patch.object(m.sys.stdin,'isatty',return_value=False),\
             patch('builtins.input') as prompt,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--activate']),1)
        prompt.assert_not_called()

    def test_wrong_approval_phrase_stops_before_lock(self):
        checker=SimpleNamespace(check=Mock())
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m,'load',side_effect=[checker,object()]),\
             patch.object(m.sys.stdin,'isatty',return_value=True),\
             patch.object(m.sys.stderr,'isatty',return_value=True),\
             patch('builtins.input',return_value='NOT APPROVED'),\
             patch.object(m,'LOCK',Path('/unlikely/release-lock-does-not-exist')),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--activate']),1)
        checker.check.assert_called_once()


    def make_activation_mocks(self):
        verifier=SimpleNamespace(import_pinned_helper=lambda:SimpleNamespace())
        checker=SimpleNamespace(check=Mock(), load_pinned=Mock(return_value=verifier),
                                VERIFY=Path('/verify'), VERIFY_HASH='hash')
        previous=SimpleNamespace()
        return checker,previous

    def test_approved_activation_preflight_rechecked_under_lock(self):
        checker,prior=self.make_activation_mocks()
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'deploy.lock';lock.write_text('')
            with (
                patch.object(m,'LOCK',lock),
                patch.object(m.os,'geteuid',return_value=0),
                patch.object(m,'load',side_effect=[checker,prior]),
                patch.object(m.sys.stdin,'isatty',return_value=True),
                patch.object(m.sys.stderr,'isatty',return_value=True),
                patch('builtins.input',return_value=m.APPROVAL),
                patch.object(m,'Release') as release,
            ):
                inst=release.return_value
                self.assertEqual(m.main(['--activate']),0)
        self.assertEqual(checker.check.call_count,2)
        inst.snapshot.assert_called_once()
        inst.activate.assert_called_once()
        inst.rollback.assert_not_called()

    def test_activation_failure_runs_candidate_rollback(self):
        checker,prior=self.make_activation_mocks()
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'deploy.lock';lock.write_text('')
            with (
                patch.object(m,'LOCK',lock),
                patch.object(m.os,'geteuid',return_value=0),
                patch.object(m,'load',side_effect=[checker,prior]),
                patch.object(m.sys.stdin,'isatty',return_value=True),
                patch.object(m.sys.stderr,'isatty',return_value=True),
                patch('builtins.input',return_value=m.APPROVAL),
                patch.object(m,'Release') as release,
            ):
                inst=release.return_value
                inst.activate.side_effect=m.Stop('SYNTHETIC_FAILURE')
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(m.main(['--activate']),1)
        inst.rollback.assert_called_once()

    def test_rollback_failure_requires_manual_review(self):
        checker,prior=self.make_activation_mocks()
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'deploy.lock';lock.write_text('')
            with (
                patch.object(m,'LOCK',lock),
                patch.object(m.os,'geteuid',return_value=0),
                patch.object(m,'load',side_effect=[checker,prior]),
                patch.object(m.sys.stdin,'isatty',return_value=True),
                patch.object(m.sys.stderr,'isatty',return_value=True),
                patch('builtins.input',return_value=m.APPROVAL),
                patch.object(m,'Release') as release,
            ):
                inst=release.return_value
                inst.activate.side_effect=m.Stop('SYNTHETIC_FAILURE')
                inst.rollback.side_effect=m.Stop('SYNTHETIC_RECOVERY_FAILURE')
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(m.main(['--activate']),2)
        self.assertIn('RECOVERY_INCOMPLETE',output.getvalue())

    def test_prior_start_requires_normalised_candidate_identity(self):
        src=Path(m.__file__).read_text()
        self.assertIn("'ACT_TRACKING_ACTIVATION':str(self.record)",src)
        self.assertIn("'activation_nonce':str(self.record)",src)
        self.assertIn("'name':NAME,'cwd':str(self.stage.CANDIDATE)",src)
        self.assertNotIn('stripe.PaymentIntent',src)

    def test_no_live_switch_in_check_mode(self):
        src=Path(m.__file__).read_text()
        check_branch=src[src.index('if args.check:'):src.index("need(sys.stdin.isatty()",src.index('if args.check:'))]
        self.assertNotIn('release.activate()',check_branch)
        self.assertNotIn("'reload'",check_branch)

    def test_successful_activation_is_distinct_from_payment(self):
        self.assertNotIn('PaymentIntent.create',Path(m.__file__).read_text())
        self.assertNotIn('confirmCardPayment',Path(m.__file__).read_text())
        self.assertEqual(m.APPROVAL,'APPROVE ACT TEST FRONTEND SWITCH')

if __name__=='__main__':unittest.main(verbosity=2)
