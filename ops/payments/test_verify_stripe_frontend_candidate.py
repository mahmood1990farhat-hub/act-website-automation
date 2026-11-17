"""Isolated synthetic post-build tests; never connect to Stripe or modify live services."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('candidate_verifier',Path(__file__).with_name('verify_stripe_frontend_candidate.py'))
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

class FakeStage:
    def __init__(self,root):
        self.CANDIDATE=root/'candidate';self.NEW_ASSETS=root/'union'
        self.ACTIVE=root/'active';self.OLD_ASSETS=root/'old';self.REPO=root/'repo'
        self.RECORD=root/'private'; self.RECORD.mkdir(mode=0o700)
        self.CANDIDATE.mkdir();self.NEW_ASSETS.mkdir();self.ACTIVE.mkdir();self.OLD_ASSETS.mkdir()
        (self.CANDIDATE/'.next/static/chunks').mkdir(parents=True)
        (self.CANDIDATE/'.next/BUILD_ID').write_text('new123')
        (self.CANDIDATE/'.next/static/chunks/new.js').write_text('const pk = "'+NEW+'";')
        (self.OLD_ASSETS/'old.js').write_text('legacy')
        (self.NEW_ASSETS/'old.js').write_text('legacy')
        (self.NEW_ASSETS/'chunks').mkdir()
        (self.NEW_ASSETS/'chunks/new.js').write_text('const pk = "'+NEW+'";')
        self.files={}
        for rel in v.SOURCE_PATHS:
            text='pinned source:' + rel
            (self.CANDIDATE/rel).parent.mkdir(parents=True,exist_ok=True)
            (self.CANDIDATE/rel).write_text(text)
            self.files[rel]=text.encode()
        self.base={'nginx_sha256':'a'*64,'active_build_id':'old123',
            'backend_env_sha256':'b'*64,'pid':1234,
            'active_public':{'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY':OLD}}
        self.plan={
            'status':'PREPARED_NOT_ACTIVATED','source_sha':v.FRONT_SHA,'backend_sha':v.BACK_SHA,
            'old_build_id':'old123','new_build_id':'new123','candidate':str(self.CANDIDATE),
            'candidate_assets':str(self.NEW_ASSETS),'old_release':str(self.ACTIVE),
            'old_assets':str(self.OLD_ASSETS),'nginx_sha256':'a'*64,'backend_env_sha256':'b'*64,
            'old_public_key_sha256':v.hash_bytes(OLD.encode()),'new_public_key_sha256':v.hash_bytes(NEW.encode()),
            'activation_authorized':False,'webhook_changed':False,
            'backend_changed':False,'current_frontend_changed':False}
        with (self.RECORD/'plan.json').open('w') as out:json.dump(self.plan,out)
        (self.RECORD/'plan.json').chmod(0o600)

    def js_keys(self,_):return {NEW.encode()}
    def local_state(self):return dict(self.base)
    def command(self,args,**kwargs):
        if args[0]=='/usr/bin/ss':return b''
        if args[0]=='git':
            rel=args[-1].split(':act_website-main/')[1]
            return self.files[rel]
        raise RuntimeError('Unapproved test subprocess')

OLD='pk_test_'+'O'*32
NEW='pk_test_'+'N'*32

class CandidateVerifierTests(unittest.TestCase):
    def setUp(self):
        self.ctx=tempfile.TemporaryDirectory()
        self.f=FakeStage(Path(self.ctx.name))
    def tearDown(self):self.ctx.cleanup()

    def test_complete_candidate_preserved(self):
        v.validate_plan(self.f,self.f.plan,self.f.base)
        self.assertEqual(v.validate_candidate(self.f,self.f.plan,self.f.base),2)

    def test_read_only_entrypoint(self):
        with patch.object(v,'import_pinned_helper',return_value=self.f),patch.object(v.os,'geteuid',return_value=0):
            out,err=io.StringIO(),io.StringIO()
            with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                code=v.main()
        self.assertEqual(code,0)
        self.assertIn('ACTIVATION_NOT_APPROVED',out.getvalue())
        self.assertNotIn(NEW,out.getvalue()+err.getvalue())
        self.assertNotIn(OLD,out.getvalue()+err.getvalue())

    def test_private_plan_permissions_enforced(self):
        p=self.f.RECORD/'plan.json'
        self.assertEqual(v.private_plan(p)['source_sha'],v.FRONT_SHA)
        p.chmod(0o644)
        with self.assertRaisesRegex(v.Stop,'PLAN_NOT_PRIVATE_OR_INVALID'):v.private_plan(p)
        p.chmod(0o600)
        self.f.RECORD.chmod(0o755)
        with self.assertRaisesRegex(v.Stop,'PLAN_DIRECTORY_NOT_PRIVATE'):v.private_plan(p)

    def test_wrong_or_activated_plan_refused(self):
        for field,value in [('source_sha','f'*40),('candidate','/tmp/not-our-candidate'),('status','ACTIVATED'),('activation_authorized',True),('nginx_sha256','f'*64),('backend_env_sha256','x'*64)]:
            p={**self.f.plan,field:value}
            with self.subTest(field=field),self.assertRaisesRegex(v.Stop,'PLAN_BASELINE_MISMATCH'):
                v.validate_plan(self.f,p,self.f.base)

    def test_reused_old_key_refused(self):
        p={**self.f.plan,'new_public_key_sha256':v.hash_bytes(OLD.encode())}
        with self.assertRaisesRegex(v.Stop,'NEW_KEY_FINGERPRINT_INVALID'):
            v.validate_plan(self.f,p,self.f.base)

    def test_compiled_key_drift_refused(self):
        with patch.object(self.f,'js_keys',return_value={OLD.encode()}):
            with self.assertRaisesRegex(v.Stop,'CANDIDATE_KEY_FINGERPRINT_MISMATCH'):
                v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_pinned_checkout_code_modified_refused(self):
        path=self.f.CANDIDATE/v.SOURCE_PATHS[0]
        path.write_text('modified!')
        with self.assertRaisesRegex(v.Stop,'PINNED_APP_FILE_CHANGED'):
            v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_asset_missing_or_extra_refused(self):
        (self.f.NEW_ASSETS/'old.js').unlink()
        with self.assertRaisesRegex(v.Stop,'ASSET_UNION_NOT_COMPLETE_OR_CHANGED'):
            v.validate_candidate(self.f,self.f.plan,self.f.base)
        (self.f.NEW_ASSETS/'old.js').write_text('legacy')
        (self.f.NEW_ASSETS/'sneaky.txt').write_text('extra')
        with self.assertRaisesRegex(v.Stop,'ASSET_UNION_NOT_COMPLETE_OR_CHANGED'):
            v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_content_collision_refused(self):
        (self.f.CANDIDATE/'.next/static/old.js').write_text('different')
        with self.assertRaisesRegex(v.Stop,'OLD_NEW_ASSET_COLLISION'):
            v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_unapproved_listener_refused(self):
        real=self.f.command
        def fake(args,**kwargs):
            if args[0]=='/usr/bin/ss':return b'LISTEN...'
            return real(args,**kwargs)
        with patch.object(self.f,'command',side_effect=fake):
            with self.assertRaisesRegex(v.Stop,'CANDIDATE_PORT_UNEXPECTEDLY_ACTIVE'):
                v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_symlink_assets_refused(self):
        (self.f.NEW_ASSETS/'symlink').symlink_to('/etc/hosts')
        with self.assertRaisesRegex(v.Stop,'ASSET_LINK_NOT_ALLOWED'):
            v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_active_release_drift_refused(self):
        with patch.object(self.f,'local_state',return_value={**self.f.base,'pid':999}):
            with self.assertRaisesRegex(v.Stop,'ACTIVE_RELEASE_DRIFT'):
                v.validate_candidate(self.f,self.f.plan,self.f.base)

    def test_no_root_refused(self):
        with patch.object(v.os,'geteuid',return_value=1000),patch.object(v,'import_pinned_helper') as loader:
            out=io.StringIO()
            with contextlib.redirect_stderr(out):self.assertEqual(v.main(),1)
            self.assertIn('ROOT_READ_ONLY_REQUIRED',out.getvalue())
            loader.assert_not_called()

if __name__=='__main__':unittest.main()
