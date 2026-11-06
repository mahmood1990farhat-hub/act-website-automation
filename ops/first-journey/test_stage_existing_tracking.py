"""Finite staging guards only; no VPS, GitHub, npm, service or provider calls."""
import importlib.util
import io
import os
import json
import subprocess
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('stage', Path(__file__).with_name('stage_existing_tracking.py'))
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


class StagingGuards(unittest.TestCase):
    def test_remote_identity_rejects_other_host_or_repository(self):
        stage.verify_remote('git@github.com:mahmood1990farhat-hub/act-website-automation.git')
        stage.verify_remote('https://github.com/mahmood1990farhat-hub/act-website-automation.git')
        for value in ('https://github.com.evil.test/mahmood1990farhat-hub/act-website-automation',
                      'https://github.com/other/repository.git'):
            with self.assertRaises(stage.Stop):
                stage.verify_remote(value)

    def test_production_diff_does_not_allow_extra_api_changes(self):
        with patch.object(stage, 'git', return_value=b'act_backend-main/apps/trips/consumers.py\nact_backend-main/apps/payments/views.py\n'):
            with self.assertRaises(stage.Stop):
                stage.verify_diff('base','candidate','act_backend-main',{'apps/trips/consumers.py'})
        with patch.object(stage,'git',return_value=b'act_backend-main/apps/trips/consumers.py\nact_backend-main/tests/test_tracking.py\n'):
            self.assertEqual(stage.verify_diff('base','candidate','act_backend-main',{'apps/trips/consumers.py'}), ['apps/trips/consumers.py'])
        isolated_tests=b'\n'.join(('act_backend-main/'+name).encode() for name in stage.BACK_TEST_FILES)
        with patch.object(stage,'git',return_value=b'act_backend-main/apps/trips/consumers.py\n'+isolated_tests):
            self.assertEqual(stage.verify_diff('base','candidate','act_backend-main',{'apps/trips/consumers.py'}), ['apps/trips/consumers.py'])
        with patch.object(stage,'git',return_value=b'act_backend-main/apps/trips/consumers.py\nact_backend-main/myProject/settings/base.py'):
            with self.assertRaises(stage.Stop): stage.verify_diff('base','candidate','act_backend-main',{'apps/trips/consumers.py'})

    def test_source_archive_rejects_links_and_parent_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            for number, (name, kind) in enumerate((('act_backend-main/link',tarfile.SYMTYPE),('act_backend-main/../../escape',tarfile.REGTYPE))):
                buffer = io.BytesIO()
                with tarfile.open(fileobj=buffer,mode='w') as archive:
                    item=tarfile.TarInfo(name); item.type=kind; item.linkname='/private/secret'
                    archive.addfile(item)
                with patch.object(stage,'git',return_value=buffer.getvalue()):
                    with self.assertRaises(stage.Stop):
                        stage.export_subtree('sha','act_backend-main',Path(temporary)/str(number))
            self.assertFalse((Path(temporary)/'escape').exists())

    def test_existing_release_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); keep=root/'keep'; keep.write_text('existing')
            with patch.object(stage,'git') as git:
                with self.assertRaises(stage.Stop):
                    stage.export_subtree('sha','act_backend-main',root)
                git.assert_not_called()
            self.assertEqual(keep.read_text(),'existing')

    def test_route_candidate_and_rollback_preserve_backend_routes(self):
        old=(f'location / {{\n proxy_pass http://127.0.0.1:3002;\n}}\n'
             f'location /api/places {{\n proxy_pass http://127.0.0.1:3002;\n}}\n'
             f'location /api/place-details {{\n proxy_pass http://127.0.0.1:3002;\n}}\n'
             f'location /_next/static/ {{\n alias {stage.OLD_ASSETS}/;\n}}\n'
             'location /ws/ { proxy_pass http://unix:/run/act.sock; }\n').encode()
        candidate,rollback=stage.route_pair(old,Path('/new/public/assets'))
        self.assertEqual(candidate.count(b'127.0.0.1:3003'),3)
        self.assertEqual(rollback.count(b'127.0.0.1:3002'),3)
        self.assertIn(b'proxy_pass http://unix:/run/act.sock',candidate)
        self.assertIn(b'/new/public/assets/',rollback)
        self.assertNotIn(b'3001',rollback)
        with self.assertRaises(stage.Stop):
            stage.route_pair(old+b'proxy_pass http://127.0.0.1:3002;\n',Path('/new/assets'))

    def test_asset_collision_or_symlink_refuses_without_altering_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); old=root/'old'; new=root/'new'; old.mkdir();new.mkdir()
            (old/'a.js').write_text('old'); (new/'a.js').write_text('different')
            with self.assertRaises(stage.Stop): stage.copy_assets((old,new),root/'collision')
            self.assertEqual((old/'a.js').read_text(),'old')
            self.assertEqual((new/'a.js').read_text(),'different')
            (new/'a.js').unlink();(new/'link.js').symlink_to(old/'a.js')
            with self.assertRaises(stage.Stop): stage.copy_assets((old,new),root/'linked')

    def test_asset_union_contains_existing_and_new_and_keeps_shared_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); old=root/'old';new=root/'new';old.mkdir();new.mkdir()
            (old/'old.js').write_text('old');(old/'same.js').write_text('same')
            (new/'new.js').write_text('new');(new/'same.js').write_text('same')
            manifest=stage.copy_assets((old,new),root/'union')
            self.assertEqual(set(manifest),{'old.js','new.js','same.js'})
            self.assertEqual((root/'union/old.js').read_text(),'old')

    def test_public_environment_requires_same_origin_test_mode_and_configured_maps(self):
        good={'NEXT_PUBLIC_API_BASE_URL':stage.ORIGIN,'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY':'pk_test_'+'a'*24,
              'NEXT_PUBLIC_GOOGLE_MAPS_API_KEY':'AIza'+'b'*35}
        stage.validate_public_environment(good)
        for key,value in [('NEXT_PUBLIC_API_BASE_URL',stage.ORIGIN+'/api'),
                          ('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY','pk_live_'+'a'*24),
                          ('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY','synthetic-placeholder')]:
            with self.assertRaises(stage.Stop): stage.validate_public_environment(good|{key:value})

    def test_validation_master_changes_only_private_include_and_pid(self):
        original='pid /run/nginx.pid;\nhttp {\n include /etc/nginx/sites-enabled/*;\n}\n'
        output=stage.validation_master(original,[stage.SITE],Path('/private/new/candidate.conf'))
        self.assertIn('include "/private/new/candidate.conf";',output)
        self.assertIn('pid "/private/new/nginx-validation.pid";',output)
        self.assertIn('pid /run/nginx.pid;',original)

    def test_current_release_drift_stops_before_any_command_or_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            unexpected=Path(temporary)/'unexpected';unexpected.mkdir()
            current=Path(temporary)/'current';current.symlink_to(unexpected)
            with patch.object(stage,'CURRENT',current),patch.object(stage,'git') as git,patch.object(stage,'run') as run:
                with self.assertRaises(stage.Stop): stage.stage('a'*40,'b'*40)
                git.assert_not_called();run.assert_not_called()

    def test_new_backend_directory_modes_do_not_follow_shared_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);new=root/'new';nested=new/'nested';nested.mkdir(parents=True)
            shared=root/'shared';shared.mkdir();shared.chmod(0o700)
            (new/'linked').symlink_to(shared, target_is_directory=True)
            new.chmod(0o700);nested.chmod(0o700)
            stage.ownership(new,os.getuid(),os.getgid(),directory_mode=0o750)
            self.assertEqual(new.stat().st_mode & 0o777,0o750)
            self.assertEqual(nested.stat().st_mode & 0o777,0o750)
            self.assertEqual(shared.stat().st_mode & 0o777,0o700)

    def test_passive_pm2_rpc_only_reads_existing_transport(self):
        wrapper=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
let output='',closed=false,requested=false,connected='';
const listeners={};
const request={once:(name,callback)=>{listeners[name]=callback;},close:()=>{closed=true;},connect:value=>{connected=value;listeners.connect();}};
const fs={existsSync:()=>true};
const axon={socket:type=>{assert.equal(type,'req');return request;}};
const rpc={Client:class {constructor(req){assert.equal(req,request);}call(name,args,cb){assert.equal(name,'getMonitorData');assert.deepEqual(JSON.parse(JSON.stringify(args)),{});requested=true;cb(null,[{name:'existing'}]);}}};
let exitCode=null;
try {vm.runInNewContext(SOURCE,{
 require:name=>{if(name==='fs')return fs;if(name==='path')return require('node:path');if(name==='/installed/pm2/modules/pm2-axon')return axon;if(name==='/installed/pm2/modules/pm2-axon-rpc')return rpc;throw Error('Unexpected dependency: '+name);},
 process:{argv:['node','/installed/pm2','/existing/rpc.sock'],stdout:{write:(text,cb)=>{output+=text;cb();}},exit:code=>{exitCode=code;throw Error('completed');}},
 setTimeout:()=>1,clearTimeout:()=>{}
});}catch(error){if(exitCode===null)throw error;}
assert.equal(exitCode,0);assert.equal(connected,'/existing/rpc.sock');assert.equal(requested,true);assert.equal(closed,true);
assert.deepEqual(JSON.parse(output),[{name:'existing'}]);
'''.replace('SOURCE',json.dumps(stage.PM2_READ_ONLY))
        result=subprocess.run(['node','-'],input=wrapper,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':
    unittest.main(verbosity=2)
