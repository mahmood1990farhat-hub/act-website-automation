"""Pure and synthetic no-write release preflight cases; no live service calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location(
    'act_stripe_frontend_switch_check',
    Path(__file__).with_name('check_stripe_frontend_switch.py'))
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def nginx_config():
    return (b'server {\n'
            + b'  proxy_pass http://127.0.0.1:3004;\n'*3
            + b'  alias /old-assets/;\n'
            + b'  location /api/ { proxy_pass http://127.0.0.1:8000; }\n}\n')


class ReadOnlySwitchTests(unittest.TestCase):
    def test_only_three_frontend_routes_and_one_alias_change(self):
        old=nginx_config()
        new=v.propose_config(old,Path('/old-assets'),Path('/new-assets'))
        self.assertEqual(new.count(b'proxy_pass http://127.0.0.1:3005;'),3)
        self.assertEqual(new.count(b'alias /new-assets/;'),1)
        self.assertIn(b'proxy_pass http://127.0.0.1:8000;',new)
        back=new.replace(b'127.0.0.1:3005',b'127.0.0.1:3004').replace(b'/new-assets/',b'/old-assets/')
        self.assertEqual(back,old)

    def test_no_change_when_one_route_missing(self):
        with self.assertRaisesRegex(v.Stop,'EXPECTED_THREE_OLD_FRONTEND_UPSTREAMS'):
            v.propose_config(nginx_config().replace(
                b'proxy_pass http://127.0.0.1:3004;',b'',1),
                Path('/old-assets'),Path('/new-assets'))

    def test_no_change_when_extra_route_present(self):
        with self.assertRaisesRegex(v.Stop,'EXPECTED_THREE_OLD_FRONTEND_UPSTREAMS'):
            v.propose_config(nginx_config()+b'proxy_pass http://127.0.0.1:3004;',
                             Path('/old-assets'),Path('/new-assets'))

    def test_wrong_static_alias_refused(self):
        for input_bytes in (nginx_config().replace(b'/old-assets/',b'/wrong/'),
                            nginx_config()+b'alias /old-assets/;'):
            with self.subTest(input=input_bytes[-20:]),self.assertRaisesRegex(
                v.Stop,'EXPECTED_ONE_OLD_STATIC_ALIAS'):
                v.propose_config(input_bytes,Path('/old-assets'),Path('/new-assets'))

    def test_existing_new_route_that_defeats_exact_inverse_refused(self):
        data=nginx_config()+b'  proxy_pass http://127.0.0.1:3005;\n'
        with self.assertRaisesRegex(v.Stop,'PROPOSED_FRONTEND_ROUTES_INVALID'):
            v.propose_config(data,Path('/old-assets'),Path('/new-assets'))

    def test_invalid_encoding_is_not_leaked(self):
        err=io.StringIO()
        with patch.object(v,'check',side_effect=ValueError('secret-token')), \
             contextlib.redirect_stderr(err):
            self.assertEqual(v.main(),1)
        self.assertNotIn('secret-token',err.getvalue())
        self.assertIn('FRONTEND_SWITCH_PREFLIGHT_UNAVAILABLE',err.getvalue())

    def test_main_success_never_prints_any_provider_keys(self):
        out=io.StringIO()
        with patch.object(v,'check',return_value=True),contextlib.redirect_stdout(out):
            self.assertEqual(v.main(),0)
        self.assertIn('NO_CHANGES; NO_ACTIVATION_COMMAND',out.getvalue())
        self.assertNotIn('pk_test_',out.getvalue())

    def test_main_stops_on_known_source_drift(self):
        out=io.StringIO()
        with patch.object(v,'check',side_effect=v.Stop('NGINX_LIVE_SITE_DRIFT')), \
             contextlib.redirect_stderr(out):
            self.assertEqual(v.main(),1)
        self.assertIn('NGINX_LIVE_SITE_DRIFT',out.getvalue())

    def fixture(self,td):
        root=Path(td)
        site_file=root/'site.conf'
        original=nginx_config()
        site_file.write_bytes(original)
        link=root/'site-link'
        link.symlink_to(site_file)
        stage=SimpleNamespace(
            RECORD=root,OLD_ASSETS=Path('/old-assets'),NEW_ASSETS=Path('/new-assets'),
            local_state=Mock(return_value={'nginx_sha256':v.hash_bytes(original)}))
        verifier=SimpleNamespace(
            import_pinned_helper=lambda:stage,private_plan=Mock(return_value={}),
            validate_plan=Mock(),validate_candidate=Mock())
        old=SimpleNamespace()
        return link,stage,verifier,old

    def test_check_runs_existing_guards_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            site,stage,verifier,old=self.fixture(td)
            before=site.resolve().read_bytes()
            with patch.object(v.os,'geteuid',return_value=0), \
                 patch.object(Path,'is_relative_to',return_value=True), \
                 patch.object(v,'SITE',site), \
                 patch.object(v,'load_pinned',side_effect=[verifier,old]), \
                 patch.object(v,'run',return_value=b''), \
                 patch.object(v,'check_pm2',return_value=True) as pm:
                self.assertTrue(v.check())
            self.assertEqual(site.resolve().read_bytes(),before)
            self.assertEqual(verifier.validate_candidate.call_count,1)
            pm.assert_called_once_with(old,stage)

    def test_check_refuses_occupied_new_port(self):
        with tempfile.TemporaryDirectory() as td:
            site,stage,verifier,old=self.fixture(td)
            with patch.object(v.os,'geteuid',return_value=0), \
                 patch.object(Path,'is_relative_to',return_value=True), \
                 patch.object(v,'SITE',site), \
                 patch.object(v,'load_pinned',side_effect=[verifier,old]), \
                 patch.object(v,'run',return_value=b'LISTEN 0 128') as run, \
                 patch.object(v,'check_pm2') as pm:
                with self.assertRaisesRegex(v.Stop,'NEW_FRONTEND_PORT_ALREADY_USED'):
                    v.check()
            pm.assert_not_called()

    def test_check_refuses_source_mismatch_before_pm2(self):
        with tempfile.TemporaryDirectory() as td:
            site,stage,verifier,old=self.fixture(td)
            stage.local_state.return_value={'nginx_sha256':'0'*64}
            with patch.object(v.os,'geteuid',return_value=0), \
                 patch.object(Path,'is_relative_to',return_value=True), \
                 patch.object(v,'SITE',site), \
                 patch.object(v,'load_pinned',side_effect=[verifier,old]), \
                 patch.object(v,'check_pm2') as pm:
                with self.assertRaisesRegex(v.Stop,'NGINX_LIVE_SITE_DRIFT'):
                    v.check()
            pm.assert_not_called()

    def test_pm2_denies_unexpected_process_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            home=root/'pm2';home.mkdir()
            s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            try:
                s.bind(str(home/'rpc.sock'))
                (home/'pm2.pid').write_text(str(os.getpid()))
                dump=home/'dump.pm2'
                dump.write_text(json.dumps([{'name':'act'}]))
                previous=SimpleNamespace(
                    PM2_HOME=home,DUMP=dump,NODE=Path('/node'),PM2_READ='JS',
                    PM2_ROOT=Path('/pm2'),act_env=lambda:{},LAUNCH=('pm_cwd',))
                with patch.object(v,'run',return_value=json.dumps([{'name':'act'}]).encode()):
                    with self.assertRaisesRegex(v.Stop,'CURRENT_PM2_INVENTORY_DRIFT'):
                        v.check_pm2(previous,SimpleNamespace(ACTIVE=root))
            finally:
                s.close()

    def test_nonroot_no_read_at_all(self):
        with patch.object(v.os,'geteuid',return_value=1001),\
             patch.object(v,'load_pinned') as loader:
            with self.assertRaisesRegex(v.Stop,'ROOT_READ_ONLY_REQUIRED'):
                v.check()
            loader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
