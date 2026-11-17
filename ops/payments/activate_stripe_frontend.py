#!/usr/bin/env python3
"""Approval-gated ACT frontend-only Stripe TEST publishable-key activation.

--check does not mutate. --activate requires explicit separate owner approval,
root TTY, locked release checks and records. Preserves the old 3004 frontend,
backend, keys and 149-file candidate. Rolls back only this activation's changes.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
sys.dont_write_bytecode = True
import time
from urllib.parse import quote

HERE = Path('/root/act-stripe-readonly')
CHECKER = HERE / 'check_stripe_frontend_switch.py'
CHECKER_HASH = 'd156846430f90bd89981f6c773ece5bf61d0bef82db4e12e66fd74ffe2b13a63'
PRIOR = HERE / 'passenger_frontend_release.py'
PRIOR_HASH = '2c880f9e116dad51b5acf973f49b992dbe8c8af4fca1883bd8f718b440151254'
RECORD = Path('/root/act-release-backup/stripe-frontend-activation-20261117')
LOCK = Path('/run/lock/act-backend-deploy.lock')
NAME = 'act-stripe-pk-02e59f9'
PORT = 3005
DOMAIN = 'airportandcitytransfer.com'
APPROVAL = 'APPROVE ACT TEST FRONTEND SWITCH'

class Stop(Exception):
    """Only fixed safe status codes should occur here."""

def need(ok, code):
    if not ok: raise Stop(code)

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def regular(path):
    need(path.is_file() and not path.is_symlink(), 'EXPECTED_REGULAR_FILE')
    return path.read_bytes()

def load(path, expected, name):
    need(digest(regular(path)) == expected, 'PINNED_SOURCE_HASH_DRIFT')
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec is not None and spec.loader is not None, 'PINNED_SOURCE_UNAVAILABLE')
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def command(argv, *, env=None, data=None, timeout=35):
    try:
        p=subprocess.run([str(x) for x in argv], input=data, env=env,
                         capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise Stop('RELEASE_COMMAND_UNAVAILABLE') from None
    need(p.returncode == 0, 'RELEASE_COMMAND_FAILED')
    return p.stdout

def packed(obj):
    return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()

def journal(record,label):
    path=record / (label+'.json')
    with path.open('xb') as out:
        os.fchmod(out.fileno(),0o600)
        out.write(packed({'status':label,'payment_attempted':False,
                          'backend_modified':False,'record':str(record)}))
        out.flush();os.fsync(out.fileno())

def write_new(path, blob):
    with path.open('xb') as stream:
        os.fchmod(stream.fileno(),0o600)
        stream.write(blob);stream.flush();os.fsync(stream.fileno())

def process_rows(prior):
    return json.loads(command(['/usr/sbin/runuser','-u','act','--',prior.NODE,
        '-e',prior.PM2_READ,prior.PM2_ROOT,prior.PM2_HOME/'rpc.sock'],
        env=prior.act_env(),timeout=25))

def http(address, *, origin=False, direct=False):
    args=['/usr/bin/curl','--silent','--show-error','--noproxy','*',
          '--connect-timeout','3','--max-time','8','--max-filesize','16777216',
          '-H','Accept-Encoding: identity','-H','Cache-Control: no-cache',
          '-w','\n%{http_code}']
    if direct:
        args+=['-H','Host: '+DOMAIN,'-H','X-Forwarded-Proto: https']
    if origin:
        args+=['--insecure','--resolve',DOMAIN+':443:127.0.0.1']
    raw=command([*args,address],timeout=12)
    try: body,status=raw.rsplit(b'\n',1)
    except ValueError: raise Stop('INVALID_HTTP_RESPONSE') from None
    need(status==b'200','FRONTEND_HTTP_NOT_200')
    return body

def page_assets(prior, html, *, build_id, other_id, expected=None):
    need(build_id.encode() in html and other_id.encode() not in html,
         'FRONTEND_BUILD_ID_MISMATCH')
    assets=prior.html_assets(html)
    need(bool(assets),'FRONTEND_HTML_NO_STATIC_ASSETS')
    if expected is not None: need(assets==expected,'FRONTEND_HTML_ASSETS_DRIFT')
    return assets

def verify_public(prior, stage, plan, expected_assets, *, rollback=False):
    build_id=plan['old_build_id'] if rollback else plan['new_build_id']
    other_id=plan['new_build_id'] if rollback else plan['old_build_id']
    union=stage.OLD_ASSETS if rollback else stage.NEW_ASSETS
    last='PUBLIC_FRONTEND_NOT_VERIFIED'
    for attempt in range(3):
        try:
            nonce=secrets.token_hex(10)
            for origin in (True,False):
                page=http('https://'+DOMAIN+'/en?act_stripe_check='+nonce, origin=origin)
                assets=page_assets(prior,page,build_id=build_id,other_id=other_id,
                                   expected=expected_assets)
                kinds=set()
                for item in sorted(assets):
                    ext=Path(item).suffix
                    if ext not in ('.js','.css') or ext in kinds: continue
                    kinds.add(ext)
                    target=union/item.removeprefix('/_next/static/')
                    need(target.is_file() and not target.is_symlink(),
                         'EXPECTED_STATIC_ASSET_MISSING')
                    result=http('https://'+DOMAIN+quote(item,safe='/._-')+
                                '?act_stripe_check='+nonce,origin=origin)
                    need(digest(result)==digest(regular(target)),
                         'PUBLIC_ASSET_HASH_MISMATCH')
                need('.js' in kinds,'NO_JAVASCRIPT_ASSET_CHECK')
            return
        except Stop as exc:
            last=str(exc)
            if attempt<2: time.sleep(2)
    raise Stop(last)

class Release:
    def __init__(self, checker, prior, stage):
        self.chk, self.prior, self.stage=checker,prior,stage
        self.record=None
        self.started=False
        self.saved=False
        self.switched=False
        self.reloaded=False
        self.complete=False
        self.new_dump=None

    def snapshot(self):
        self.chk.check()  # the previously successful read-only owner preflight
        stage=self.stage
        self.plan=json.loads(regular(stage.RECORD/'plan.json'))
        self.baseline=stage.local_state()
        # Stripe's previously verified test publishable key can expire again.
        # Refresh its SAME-account access with GETs, not another payment attempt.
        keyset=stage.js_keys(stage.CANDIDATE)
        need(len(keyset)==1,'STAGED_TEST_PUBLIC_KEY_INVALID')
        stage.verify_candidate(next(iter(keyset)).decode(),
                               self.baseline['active_public']['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'],
                               stage.read_verified_helper())
        self.site=stage.SITE.resolve(strict=True)
        self.original=regular(self.site)
        self.proposed=self.chk.propose_config(self.original,stage.OLD_ASSETS,
                                              stage.NEW_ASSETS)
        self.original_dump=regular(self.prior.DUMP)
        self.saved_list=json.loads(self.original_dump)
        self.rows=process_rows(self.prior)
        need(len(self.rows)==4 and len(self.saved_list)==4,
             'EXPECTED_FOUR_OLD_FRONTENDS')
        self.ids=[self.prior.identity(row) for row in self.rows]
        self.backend=self.prior.Release(self.prior.REVIEWED_SHA).backend()
        need(self.backend['environment_hash']==self.baseline['backend_env_sha256'],
             'BACKEND_ENV_BASELINE_MISMATCH')
        need(not RECORD.exists() and not RECORD.is_symlink(),
             'PRIOR_ACTIVATION_RECORD_PRESENT')
        self.current_html=http('http://127.0.0.1:3004/en',direct=True)
        self.old_assets=page_assets(self.prior,self.current_html,
                                   build_id=self.plan['old_build_id'],
                                   other_id=self.plan['new_build_id'])

    def guard(self, expected_route):
        need(regular(self.site)==expected_route,'LIVE_SITE_PREIMAGE_DRIFT')
        need(self.prior.Release(self.prior.REVIEWED_SHA).backend()==self.backend,
             'BACKEND_PROCESS_OR_ENV_CHANGED')
        rows=process_rows(self.prior)
        need(len(rows) in (4,5),'FRONTEND_PROCESS_COUNT_DRIFT')
        for expected in self.ids:
            need(any(self.prior.identity(row)==expected for row in rows),
                 'PRESERVED_FRONTEND_PROCESS_DRIFT')
        return rows

    def private_record(self):
        RECORD.mkdir(mode=0o700)
        self.record=RECORD
        journal(RECORD,'RELEASE_PREPARATION_STARTED')
        write_new(RECORD/'nginx.before.conf',self.original)
        write_new(RECORD/'pm2.before.json',self.original_dump)
        write_new(RECORD/'nginx.proposed.conf',self.proposed)
        write_new(RECORD/'candidate.plan.json',packed({
            'frontend_source':self.plan['source_sha'],
            'backend_source':self.plan['backend_sha'],
            'old_build_id':self.plan['old_build_id'],
            'new_build_id':self.plan['new_build_id'],
            'old_nginx_sha256':digest(self.original),
            'proposed_nginx_sha256':digest(self.proposed),
            'old_pm2_sha256':digest(self.original_dump),
            'activated':False}))
        for label,contents in [('proposed',self.proposed),('rollback',self.original)]:
            cfg=RECORD/('nginx.'+label+'.conf')
            if label=='rollback':
                write_new(cfg,contents)
            # Validate a safe synthetic full master config; don't alter live Nginx.
            master=self.prior.validation_master(regular(self.prior.MASTER),
                                               sorted(self.prior.SITE.parent.iterdir()),cfg)
            full=RECORD/('nginx.'+label+'.master.conf')
            write_new(full,master)
            command(['/usr/sbin/nginx','-t','-c',full,'-p','/etc/nginx/'],timeout=18)
        journal(RECORD,'BOTH_NGINX_CONFIGS_VALIDATED')

    def candidate_config(self):
        keyset=self.stage.js_keys(self.stage.CANDIDATE)
        need(len(keyset)==1,'CANDIDATE_PUBLIC_KEY_INVALID')
        key=next(iter(keyset)).decode()
        public={**self.baseline['active_public'],
                'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY':key}
        config={'name':NAME,'cwd':str(self.stage.CANDIDATE),
                'script':str(self.stage.CANDIDATE/'node_modules/next/dist/bin/next'),
                'interpreter':str(self.prior.NODE),
                'args':['start','--hostname','127.0.0.1','--port',str(PORT)],
                'exec_mode':'fork','instances':1,'watch':False,
                'env':{'NODE_ENV':'production','NEXT_TELEMETRY_DISABLED':'1',
                       'ACT_TRACKING_ACTIVATION':str(self.record),
                       'ACT_STRIPE_TEST_KEY_RELEASE':str(self.record),**public},
                **self.prior.POLICY}
        need(Path(config['script']).is_file(),'CANDIDATE_NEXT_EXECUTABLE_MISSING')
        return config

    def start(self):
        self.guard(self.original)
        need(regular(self.prior.DUMP)==self.original_dump,
             'PM2_SAVED_DUMP_CHANGED_BEFORE_START')
        config=self.candidate_config()
        payload={'socket':str(self.prior.PM2_HOME/'rpc.sock'),
                 'pid_file':str(self.prior.PM2_HOME/'pm2.pid'),
                 'daemon_pid':int(regular(self.prior.PM2_HOME/'pm2.pid').strip()),
                 'retained':self.ids,'identity_fields':list(self.prior.IDENTITY),
                 'config':config,'policy':self.prior.POLICY}
        self.started=True
        journal(self.record,'PM2_START_STARTED')
        command(['/usr/sbin/runuser','-u','act','--',self.prior.NODE,
                 '-e',self.prior.PM2_START,self.prior.PM2_ROOT],
                env=self.prior.act_env(),data=packed(payload),timeout=40)
        rows=self.guard(self.original)
        need(len(rows)==5,'CANDIDATE_PROCESS_COUNT_MISMATCH')
        candidate=[row for row in rows if row.get('name')==NAME]
        need(len(candidate)==1 and candidate[0].get('pid',0)>1,
             'CANDIDATE_PROCESS_IDENTITY_MISSING')
        env=candidate[0]['pm2_env']
        need(env.get('pm_cwd')==str(self.stage.CANDIDATE)
             and env.get('pm_exec_path')==config['script']
             and env.get('exec_interpreter')==config['interpreter']
             and env.get('args')==config['args']
             and env.get('env',{}).get('ACT_TRACKING_ACTIVATION')==str(self.record),
             'CANDIDATE_PM2_CONFIGURATION_MISMATCH')
        need(regular(self.prior.DUMP)==self.original_dump,
             'PM2_SAVED_DUMP_CHANGED_DURING_START')
        ready=None
        for i in range(5):
            try:
                ready=http('http://127.0.0.1:3005/en',direct=True)
                self.new_assets=page_assets(self.prior,ready,
                    build_id=self.plan['new_build_id'],
                    other_id=self.plan['old_build_id'])
                break
            except Stop:
                if i==4: raise
                time.sleep(1)
        journal(self.record,'CANDIDATE_HTTP_READY')
        return candidate[0]

    def persist(self,candidate):
        self.guard(self.original)
        need(regular(self.prior.DUMP)==self.original_dump,
             'PM2_DUMP_DRIFT_BEFORE_PERSIST')
        saved=copy.deepcopy(candidate['pm2_env'])
        for field in ('instances','pm_id','prev_restart_delay','_tree_pids'):
            saved.pop(field,None)
        self.new_dump=packed([*self.saved_list,saved])
        self.saved=True
        journal(self.record,'PM2_DUMP_UPDATE_STARTED')
        self.prior.atomic_file(self.prior.DUMP,self.new_dump,digest(self.original_dump))
        need(regular(self.prior.DUMP)==self.new_dump,'PM2_CANDIDATE_PERSISTENCE_FAILED')
        journal(self.record,'PM2_CANDIDATE_PERSISTED')

    def switch(self):
        self.guard(self.original)
        need(regular(self.prior.DUMP)==self.new_dump,'PM2_DUMP_DRIFT_BEFORE_SWITCH')
        self.switched=True
        journal(self.record,'NGINX_FRONTEND_SWITCH_STARTED')
        self.prior.atomic_file(self.site,self.proposed,digest(self.original))
        command(['/usr/sbin/nginx','-t'],timeout=18)
        self.reloaded=True
        journal(self.record,'NGINX_RELOAD_STARTED')
        command(['/usr/bin/systemctl','reload','nginx.service'],timeout=25)
        self.guard(self.proposed)
        verify_public(self.prior,self.stage,self.plan,self.new_assets,rollback=False)
        journal(self.record,'FRONTEND_STRIPE_TEST_KEY_ACTIVATED')
        self.complete=True
        print('FRONTEND_TEST_KEY_ACTIVATED; BACKEND_UNCHANGED')
        print('PAYMENT_CONFIRMATION_NOT_YET_TESTED')

    def rollback(self):
        if not self.record or not self.started or self.complete:
            return
        journal(self.record,'ROLLBACK_STARTED')
        current=regular(self.site)
        need(current in (self.original,self.proposed),'ROLLBACK_NGINX_UNRECOGNISED')
        if current==self.proposed:
            self.prior.atomic_file(self.site,self.original,digest(self.proposed))
        command(['/usr/sbin/nginx','-t'],timeout=18)
        if self.reloaded:
            command(['/usr/bin/systemctl','reload','nginx.service'],timeout=25)
        current_dump=regular(self.prior.DUMP)
        allowed=(self.original_dump,self.new_dump)
        need(current_dump in allowed,'ROLLBACK_PM2_DUMP_UNRECOGNISED')
        if current_dump!=self.original_dump:
            self.prior.atomic_file(self.prior.DUMP,self.original_dump,digest(current_dump))
        # Reuse original strict PM2 removal guard: candidate env uses its
        # reviewed ACT_TRACKING_ACTIVATION identity, bound to THIS record only.
        payload={'socket':str(self.prior.PM2_HOME/'rpc.sock'),
                 'pid_file':str(self.prior.PM2_HOME/'pm2.pid'),
                 'daemon_pid':int(regular(self.prior.PM2_HOME/'pm2.pid').strip()),
                 'retained':self.ids,'identity_fields':list(self.prior.IDENTITY),
                 'name':NAME,'cwd':str(self.stage.CANDIDATE),
                 'script':str(self.stage.CANDIDATE/'node_modules/next/dist/bin/next'),
                 'interpreter':str(self.prior.NODE),
                 'args':['start','--hostname','127.0.0.1','--port',str(PORT)],
                 'activation_nonce':str(self.record),'allow_absent':True}
        command(['/usr/sbin/runuser','-u','act','--',self.prior.NODE,
                 '-e',self.prior.PM2_REMOVE,self.prior.PM2_ROOT],
                env=self.prior.act_env(),data=packed(payload),timeout=35)
        self.guard(self.original)
        need(len(process_rows(self.prior))==4,'PM2_ROLLBACK_INCOMPLETE')
        need(regular(self.prior.DUMP)==self.original_dump,'PM2_DUMP_ROLLBACK_INCOMPLETE')
        if self.reloaded:
            verify_public(self.prior,self.stage,self.plan,self.old_assets,rollback=True)
        journal(self.record,'FRONTEND_RETURNED_TO_3004')
        print('FRONTEND_ROLLED_BACK_TO_3004; BACKEND_UNCHANGED')

    def activate(self):
        self.private_record()
        candidate=self.start()
        self.persist(candidate)
        self.switch()

class SafeParser(argparse.ArgumentParser):
    def error(self,message):
        raise Stop('ONLY_CHECK_OR_APPROVED_ACTIVATE_ACCEPTED')

def main(argv=None):
    try:
        parser=SafeParser(description=__doc__)
        mode=parser.add_mutually_exclusive_group(required=True)
        mode.add_argument('--check',action='store_true')
        mode.add_argument('--activate',action='store_true')
        args=parser.parse_args(argv)
        need(os.geteuid()==0,'ROOT_VPS_REQUIRED')
        checker=load(CHECKER,CHECKER_HASH,'act_previous_switch_preflight')
        prior=load(PRIOR,PRIOR_HASH,'act_prior_release_helper')
        checker.check()
        if args.check:
            print('PASS: RELEASE_PRECONDITIONS_READ_ONLY')
            print('NO_CHANGES; PRODUCTION_SWITCH_NOT_AUTHORISED')
            return 0
        need(sys.stdin.isatty() and sys.stderr.isatty(),
             'INTERACTIVE_OWNER_APPROVAL_REQUIRED')
        phrase=input('Enter explicitly approved frontend switch phrase: ')
        need(phrase==APPROVAL,'PRODUCTION_APPROVAL_PHRASE_MISMATCH')
        need(LOCK.is_file() and not LOCK.is_symlink(),'DEPLOYMENT_LOCK_MISSING')
        with LOCK.open('rb') as stream:
            try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise Stop('DEPLOYMENT_ALREADY_IN_PROGRESS') from None
            checker.check()  # no time-of-check/time-of-use drift under lock
            stage=checker.load_pinned(checker.VERIFY,checker.VERIFY_HASH,'act_candidate_verify')
            stage=stage.import_pinned_helper()
            release=Release(checker,prior,stage)
            release.snapshot()
            def on_interrupt(_signal, _frame):
                raise Stop('ACTIVATION_INTERRUPTED')
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            signal.signal(signal.SIGINT, on_interrupt)
            signal.signal(signal.SIGTERM, on_interrupt)
            try: release.activate()
            except (Exception,KeyboardInterrupt):
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                try:
                    release.rollback()
                except (Exception,KeyboardInterrupt):
                    print('STOPPED: RECOVERY_INCOMPLETE; PRESERVE_PRIVATE_RECORD')
                    return 2
                print('STOPPED: FRONTEND_SWITCH_ABORTED; PRESERVED_OR_ROLLED_BACK')
                return 1
        return 0
    except Stop as exc:
        print('STOPPED: '+str(exc)+'; NO_NEW_ACTIVATION',file=sys.stderr)
        return 1
    except (Exception,KeyboardInterrupt):
        print('STOPPED: FRONTEND_RELEASE_CHECK_UNAVAILABLE; NO_NEW_ACTIVATION',file=sys.stderr)
        return 1

if __name__=='__main__': sys.exit(main())
