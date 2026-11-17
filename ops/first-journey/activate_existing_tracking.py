#!/usr/bin/env python3
"""Activate the separately approved ACT tracking source pair from its staged plan.

No build, dependency install, migration, booking edit, payment change or worker
restart. Existing 3001/3002 processes and saved definitions are preserved. Only
the staged backend, one new loopback frontend and the reviewed Nginx site change.
Requires --activate and an existing root-private --record; never auto-reruns an
activation journal. All command output and operational receipts stay private.
"""
from __future__ import annotations

import argparse
import base64
import copy
import fcntl
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote, urlsplit

BACKEND_SHA = 'd77e896af9daca5a39b7a85d5b76c5821e008d23'
FRONTEND_SHA = '3a82c16f1eb648f274759b2567db4fe433720d17'
CONSUMER_HASH = 'd10d943b079041e0998daae2e4ece3a90c1b125f64107ef4676c1d51d9c55bed'
BACK_BASE = '82c0b14ad2a71e1ce3d8d1df3527431b698ac461'
FRONT_BASE = '892317fcf938fad5fa6cd9a833a79e900dcc4d8f'
BACK_ROOT = Path('/var/www/atg/atg-backend')
BACK_OLD = BACK_ROOT / 'releases/20261016T-ready-82c0b14/backend'
CURRENT = BACK_ROOT / 'current'
VENV = BACK_ROOT / 'releases/20261015T-ready-735c966/backend/.venv'
FRONT_ROOT = Path('/var/www/atg/front-end')
FRONT_OLD = FRONT_ROOT / 'releases/20261015-892317f'
FRONT_BUILD_HASH = '7e829c27388c892d02e4ba3846d1aa84ede880796fb67348fe0d39f106aa5e4a'
OLD_ASSETS = FRONT_ROOT / 'act-static-892317f-cutover'
REPO = FRONT_ROOT / 'airportandcitytransfer_repo'
BACKUP_ROOT = Path('/root/act-release-backup')
SITE = Path('/etc/nginx/sites-enabled/airportandcitytransfer')
MASTER = Path('/etc/nginx/nginx.conf')
NODE_DIR = Path('/home/act/.nvm/versions/node/v24.13.0/bin')
NODE = NODE_DIR / 'node'
PM2_ROOT = Path('/home/act/.nvm/versions/node/v24.13.0/lib/node_modules/pm2')
PM2_HOME = Path('/home/act/.pm2')
DUMP = PM2_HOME / 'dump.pm2'
DOMAIN = 'airportandcitytransfer.com'
ORIGIN = 'https://' + DOMAIN
API_PATH = '/api/trips/list-trips/'
WS_PATH = '/ws/trips/0/tracking/'  # Missing-token denial precedes any trip lookup.
POLICY = {'autorestart': True, 'restart_delay': 3000, 'max_restarts': 5, 'min_uptime': 10000}
ARGS = ['start', '--hostname', '127.0.0.1', '--port', '3003']
RETAINED = ('act', 'act-preview-892317f')
UNCHANGED_UNITS = ('act-celery-beat.service', 'act-celery-confirmations.service', 'pm2-act.service', 'nginx.service')
ENV_NAMES = ('.env.production.local', '.env.local', '.env.production', '.env')
SYSTEM_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}
LAUNCH_FIELDS = ('pm_cwd', 'pm_exec_path', 'exec_interpreter', 'args', 'exec_mode', 'env',
                 'autorestart', 'restart_delay', 'max_restarts', 'min_uptime')
FRONT_FILES = (
    'src/lib/trip-tracking-url.ts', 'src/hooks/use-trip-tracking.ts',
    'src/components/_components/dashboard/tracking/trip-tracking-provider.tsx',
    'src/components/_components/dashboard/tracking/trip-tracking-map.tsx',
    'src/components/_components/dashboard/TripsDashboard.tsx',
    'src/components/_components/Trips/MyTripsCard.tsx',
)


class Stop(Exception):
    """A sanitized, safe-to-print refusal reason."""


def require(condition, message):
    if not condition:
        raise Stop(message)


def say(message):
    """A disconnected terminal must not interrupt the approved transaction."""
    try:
        print(message, flush=True)
    except (BrokenPipeError, OSError):
        pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def fsync_parent(path):
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def private_write(path, data):
    with path.open('xb') as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    fsync_parent(path)


def regular_bytes(path):
    require(path.is_file() and not path.is_symlink(), 'A required regular file is missing or symlinked.')
    return path.read_bytes()


def private_path(path, directory=False):
    info = path.lstat()
    require(not path.is_symlink() and info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o077,
            'Activation input must remain root-private and not symlinked.')
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            'Unexpected activation input file type.')


def route_pair(original, assets):
    text = original.decode()
    port = re.compile(r'(?m)^([ \t]*proxy_pass[ \t]+)http://127\.0\.0\.1:3002([ \t]*;)')
    alias = re.compile(r'(?m)^([ \t]*alias[ \t]+)' + re.escape(str(OLD_ASSETS)) + r'/([ \t]*;)')
    require(len(port.findall(text)) == 3 and len(alias.findall(text)) == 1,
            'Routing preimage differs from the three reviewed upstreams and static alias.')
    rollback = alias.sub(lambda m: m[1] + str(assets) + '/' + m[2], text)
    candidate = port.sub(lambda m: m[1] + 'http://127.0.0.1:3003' + m[2], rollback)
    return candidate.encode(), rollback.encode()


def atomic_site(path, data, expected_hash):
    """Replace a regular file atomically; preserve owner/mode/xattrs and refuse drift."""
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Atomic target is not a single-link regular file.')
    require(sha(path.read_bytes()) == expected_hash, 'Concurrent file edit; overwrite refused.')
    descriptor, temporary = tempfile.mkstemp(prefix='.act-activate-', dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
            os.fchown(output.fileno(), info.st_uid, info.st_gid)
            os.fchmod(output.fileno(), stat.S_IMODE(info.st_mode))
            output.flush()
            os.fsync(output.fileno())
        for key in os.listxattr(path, follow_symlinks=False):
            os.setxattr(temp, key, os.getxattr(path, key, follow_symlinks=False))
        now = path.lstat()
        require((now.st_dev, now.st_ino, now.st_mtime_ns, now.st_uid, now.st_gid, now.st_mode) ==
                (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_uid, info.st_gid, info.st_mode)
                and sha(path.read_bytes()) == expected_hash, 'Concurrent file change; overwrite refused.')
        os.replace(temp, path)
        fsync_parent(path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_current(target, expected_target):
    require(CURRENT.is_symlink() and CURRENT.resolve(strict=True) == expected_target,
            'Backend pointer drift; overwrite refused.')
    info = CURRENT.lstat()
    original_link = os.readlink(CURRENT)
    require(target.is_dir() and target.resolve(strict=True) == target,
            'Backend destination is not the staged regular directory.')
    temporary = CURRENT.parent / ('.current-tracking-' + os.urandom(8).hex())
    try:
        temporary.symlink_to(target)
        os.chown(temporary, info.st_uid, info.st_gid, follow_symlinks=False)
        now = CURRENT.lstat()
        require(CURRENT.is_symlink() and os.readlink(CURRENT) == original_link and
                (now.st_dev, now.st_ino) == (info.st_dev, info.st_ino),
                'Concurrent backend pointer change; overwrite refused.')
        os.replace(temporary, CURRENT)
        fsync_parent(CURRENT)
    finally:
        temporary.unlink(missing_ok=True)


def validate_plan(record, plan):
    require(record.is_absolute() and record.parent == BACKUP_ROOT and
            re.fullmatch(r'tracking-stage-[a-z0-9_]{8}', record.name), 'Unexpected private staging record path.')
    require(plan.get('state') == 'STAGED_NOT_ACTIVE' and plan.get('backend_sha') == BACKEND_SHA
            and plan.get('frontend_sha') == FRONTEND_SHA, 'Staged source pair is not the approved tested pair.')
    tag = record.name.removeprefix('tracking-stage-')
    backend = BACK_ROOT / 'releases' / f'20261106-tracking-{BACKEND_SHA[:7]}-{tag}' / 'backend'
    frontend = FRONT_ROOT / 'releases' / f'20261106-tracking-{FRONTEND_SHA[:7]}-{tag}'
    assets = FRONT_ROOT / f'act-static-tracking-{FRONTEND_SHA[:7]}-{tag}'
    require(plan.get('backend_release') == str(backend) and plan.get('frontend_release') == str(frontend)
            and plan.get('public_assets') == str(assets), 'Staged release paths differ from the approved plan.')
    require(plan.get('live_site') == str(SITE) and plan.get('prior_upstream') == '127.0.0.1:3002'
            and plan.get('candidate_upstream') == '127.0.0.1:3003'
            and plan.get('candidate_pm2_name') == 'act-tracking-' + FRONTEND_SHA[:7]
            and plan.get('private_public_environment_file') == str(record / 'frontend-public-environment.json'),
            'Staged routing or process identity differs.')
    require(plan.get('pm2_launch') == {'cwd': str(frontend),
            'script': str(frontend / 'node_modules/next/dist/bin/next'), 'interpreter': str(NODE),
            'args': ARGS, 'env': {'NODE_ENV': 'production'}}, 'Staged PM2 launch is not the reviewed definition.')
    require(plan.get('api_origin') == ORIGIN and plan.get('stripe_public_mode') == 'test'
            and plan.get('maps_key_present') is True and plan.get('nginx_validation_passed') is True
            and plan.get('candidate_listener_started') is False, 'Staging did not finish with the required configuration.')
    require(plan.get('backend_changed_application_files') == ['apps/trips/consumers.py']
            and plan.get('frontend_changed_application_files') == sorted(FRONT_FILES),
            'Staged application scope differs.')
    backend_receipt = plan.get('backend', {})
    require(backend_receipt.get('git_sha') == BACKEND_SHA and backend_receipt.get('state') == 'STAGED_NOT_ACTIVE'
            and backend_receipt.get('consumer_sha256') == CONSUMER_HASH
            and backend_receipt.get('venv_provider') == str(VENV), 'Staged backend receipt differs.')
    for key in ('original_sha256', 'candidate_sha256', 'rollback_sha256', 'asset_manifest_sha256', 'frontend_lock_sha256'):
        require(isinstance(plan.get(key), str) and re.fullmatch('[0-9a-f]{64}', plan[key]), 'Staged checksum is missing.')
    require(isinstance(plan.get('frontend_build_id'), str) and
            re.fullmatch('[A-Za-z0-9_-]{1,128}', plan['frontend_build_id']), 'Staged frontend build ID is invalid.')


def validation_master(original, entries, candidate):
    text = original.decode()
    include = re.compile(r'(?m)^[ \t]*include[ \t]+/etc/nginx/sites-enabled/\*[ \t]*;')
    require(len(include.findall(text)) == 1 and entries.count(SITE) == 1,
            'Unexpected Nginx site include structure.')
    lines = []
    for entry in entries:
        chosen = str(candidate if entry == SITE else entry)
        require(not any(c in chosen for c in ('"', '\\', '\n', '\r', '$')), 'Unexpected Nginx include path.')
        lines.append('    include "' + chosen + '";')
    text = include.sub(lambda _: '\n'.join(lines), text)
    pid = re.compile(r'(?m)^[ \t]*pid[ \t]+[^;\n]+;')
    require(len(pid.findall(text)) <= 1, 'Ambiguous Nginx PID directive.')
    replacement = 'pid "' + str(candidate.parent / 'nginx-validation.pid') + '";'
    return (pid.sub(lambda _: replacement, text) if pid.search(text) else replacement + '\n' + text).encode()


def act_env():
    return {'HOME': '/home/act', 'USER': 'act', 'LOGNAME': 'act', 'PM2_HOME': str(PM2_HOME),
            'PATH': str(NODE_DIR) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8',
            'NODE_ENV': 'production', 'NEXT_TELEMETRY_DISABLED': '1',
            'PM2_PROGRAMMATIC': '1', 'PM2_NO_INTERACTION': 'true'}


def public_environment(values):
    require(isinstance(values, dict) and all(re.fullmatch(r'NEXT_PUBLIC_[A-Z0-9_]+', key)
            and isinstance(value, str) for key, value in values.items()), 'Captured public environment is malformed.')
    require(values.get('NEXT_PUBLIC_API_BASE_URL') == ORIGIN, 'Captured API origin differs.')
    require(re.fullmatch(r'pk_test_[A-Za-z0-9]{16,}', values.get('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY', '')),
            'Captured Stripe public key is not test mode.')
    maps = values.get('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY', '')
    require(maps.strip() and not re.search(r'placeholder|synthetic|replace|your[_ -]?key', maps, re.I),
            'Captured Maps key is missing or a placeholder.')


def pm2_identity(row):
    value = row['pm2_env']
    return {'name': row['name'], 'pm_id': row['pm_id'], 'pid': row['pid'],
            **{key: value.get(key) for key in (*LAUNCH_FIELDS, 'status', 'restart_time', 'pm_uptime')}}


def one(rows, name):
    found = [row for row in rows if row.get('name') == name]
    require(len(found) == 1, 'A required PM2 process is missing or duplicated.')
    return found[0]


def saved_matches_live(saved, live):
    require(saved.get('name') == live.get('name') and all(saved.get(key) == live['pm2_env'].get(key)
            for key in LAUNCH_FIELDS), 'Saved PM2 launch or environment differs from its live process.')


PM2_READ_ONLY = r'''
const fs=require('fs'),path=require('path'),root=process.argv[1],socket=process.argv[2];
function dep(name){const p=path.join(root,'modules',name);return fs.existsSync(p)?require(p):require(require.resolve(name,{paths:[root]}));}
const request=dep('pm2-axon').socket('req'),client=new (dep('pm2-axon-rpc').Client)(request);
const timer=setTimeout(()=>process.exit(2),15000);
request.once('error',()=>process.exit(2));
request.once('connect',()=>client.call('getMonitorData',{},(error,rows)=>{
 if(error||!Array.isArray(rows))return process.exit(2);
 clearTimeout(timer);request.close();process.stdout.write(JSON.stringify(rows),()=>process.exit(0));
}));
request.connect(socket);
'''

NODE_ENV_READ = r'''
const root=process.argv[1],silent={info(){},warn(){},error(){}};
const e=require(require.resolve('@next/env',{paths:[root]})).loadEnvConfig(root,false,silent,true).combinedEnv;
process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(e).filter(([k,v])=>k.startsWith('NEXT_PUBLIC_')&&typeof v==='string'))));
'''

# Only attach to the existing daemon. Client.start/launchDaemon are forbidden;
# executeRemote allows prepare only for this new exact launch. Other processes
# cannot be restarted, including a concurrent process with the proposed name.
PM2_START = r'''
'use strict';
const fs=require('fs'),util=require('util'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const check=(ok)=>{if(!ok)throw new Error('PM2 activation guard refused');};
const same=util.isDeepStrictEqual;
console.log=(...args)=>process.stderr.write(args.join(' ')+'\n');
const pm2=require(process.argv[1]);
const expectedConfig=JSON.parse(JSON.stringify(input.config));
const timer=setTimeout(()=>process.exit(2),25000);
const call=(obj,method,...args)=>new Promise((resolve,reject)=>obj[method](...args,(error,result)=>error?reject(error):resolve(result)));
const identity=p=>({name:p.name,pm_id:p.pm_id,pid:p.pid,...Object.fromEntries(input.identity_fields.map(k=>[k,p.pm2_env[k]??null]))});
const guard=rows=>check(rows.length===input.retained.length&&rows.every(p=>input.retained.some(w=>same(identity(p),w))));
const fail=cb=>{if(typeof cb==='function')cb(new Error('Daemon creation forbidden'));else throw new Error('Daemon creation forbidden');};
(async()=>{
 check(fs.lstatSync(input.socket).isSocket()&&Number(fs.readFileSync(input.pid_file,'utf8'))===input.daemon_pid);
 process.kill(input.daemon_pid,0);
 check(pm2.Client&&typeof pm2.Client.launchRPC==='function');
 pm2.Client.start=fail;pm2.Client.launchDaemon=fail;
 const execute=pm2.Client.executeRemote.bind(pm2.Client);
 pm2.Client.executeRemote=(method,data,cb)=>{
  if(method==='getMonitorData')return execute(method,data,cb);
  if(method!=='prepare')return cb(new Error('Unapproved PM2 method'));
  const c=expectedConfig;
  if(data.name!==c.name||data.pm_cwd!==c.cwd||data.pm_exec_path!==c.script||data.exec_interpreter!==c.interpreter||
     !same(data.args,c.args)||data.exec_mode!=='fork_mode'||data.instances!==1||
     !Object.entries(input.policy).every(([k,v])=>data[k]===v))return cb(new Error('Launch definition differs'));
  if(!Object.entries(c.env).every(([k,v])=>data.env?.[k]===v))return cb(new Error('Launch environment differs'));
  execute('getMonitorData',{},(error,rows)=>{
   if(error)return cb(error);
   try{guard(rows);}catch(e){return cb(e);}
   execute('prepare',data,cb);
  });
 };
 await call(pm2.Client,'launchRPC');
 guard(await call(pm2,'list'));
 await call(pm2,'start',{apps:[JSON.parse(JSON.stringify(expectedConfig))]});
 const rows=await call(pm2,'list');
 check(rows.length===input.retained.length+1);
 for(const w of input.retained)check(rows.some(p=>same(identity(p),w)));
 const found=rows.filter(p=>p.name===expectedConfig.name);check(found.length===1);
 process.stdout.write('ACT_PM2_RESULT='+JSON.stringify({pm_id:found[0].pm_id,pid:found[0].pid})+'\n');
})().then(()=>{clearTimeout(timer);pm2.disconnect(()=>process.exit(0));}).catch(()=>{
 clearTimeout(timer);process.stderr.write('PM2 candidate startup refused or incomplete.\n');
 pm2.disconnect(()=>process.exit(2));
});
'''

PM2_REMOVE_CANDIDATE = r'''
'use strict';
const fs=require('fs'),path=require('path'),util=require('util'),root=process.argv[1],input=JSON.parse(fs.readFileSync(0,'utf8'));
function dep(name){const p=path.join(root,'modules',name);return fs.existsSync(p)?require(p):require(require.resolve(name,{paths:[root]}));}
const req=dep('pm2-axon').socket('req'),rpc=new (dep('pm2-axon-rpc').Client)(req),same=util.isDeepStrictEqual;
const timer=setTimeout(()=>process.exit(2),25000);
const done=code=>{clearTimeout(timer);req.close();process.exit(code);};
const identity=p=>({name:p.name,pm_id:p.pm_id,pid:p.pid,...Object.fromEntries(input.identity_fields.map(k=>[k,p.pm2_env[k]??null]))});
req.once('error',()=>done(2));
req.once('connect',()=>rpc.call('getMonitorData',{},(error,rows)=>{
 if(error||!Array.isArray(rows))return done(2);
 if(!input.retained.every(w=>rows.some(p=>same(identity(p),w))))return done(2);
 const found=rows.filter(p=>p.name===input.name);
 // An unacknowledged prepare can still be waiting for PM2's asynchronous log
 // setup. An empty list then proves neither completion nor safe cancellation.
 if(found.length===0&&rows.length===input.retained.length)return done(input.allow_absent?0:2);
 if(found.length!==1||rows.length!==input.retained.length+1)return done(2);
 const p=found[0],e=p.pm2_env;
 if(e.pm_cwd!==input.cwd||e.pm_exec_path!==input.script||e.exec_interpreter!==input.interpreter||!same(e.args,input.args)||
    e.env?.ACT_TRACKING_ACTIVATION!==input.activation_nonce)return done(2);
 rpc.call('deleteProcessId',p.pm_id,(failure)=>done(failure?2:0));
}));
req.connect(input.socket);
'''


class AssetsInHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'link'):
            for key, value in attrs:
                if key in ('src', 'href') and value:
                    parsed = urlsplit(value)
                    if not parsed.netloc and parsed.path.startswith('/_next/static/'):
                        self.paths.add(parsed.path)


def html_assets(body):
    parser = AssetsInHTML()
    parser.feed(body.decode('utf-8', 'replace'))
    return parser.paths


def recv_exact(connection, count, deadline=None):
    content = bytearray()
    while len(content) < count:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'Anonymous WebSocket check exceeded its time bound.')
            connection.settimeout(min(5, remaining))
        part = connection.recv(count - len(content))
        require(part, 'Anonymous WebSocket closed before the required refusal.')
        content.extend(part)
    return bytes(content)


def websocket_frame(connection, deadline=None):
    first, second = recv_exact(connection, 2, deadline)
    require(first & 0x80 and not first & 0x70 and not second & 0x80,
            'Unexpected WebSocket frame flags.')
    length = second & 0x7f
    if length == 126:
        length = struct.unpack('!H', recv_exact(connection, 2, deadline))[0]
    elif length == 127:
        length = struct.unpack('!Q', recv_exact(connection, 8, deadline))[0]
    require(length <= 4096, 'Unexpected WebSocket response size; no payload retained.')
    return first & 0x0f, recv_exact(connection, length, deadline)


def anonymous_refusal():
    """No JWT, coordinates or trip lookup; require auth_error followed by close 4403."""
    key = base64.b64encode(os.urandom(16)).decode()
    handshake = (f'GET {WS_PATH} HTTP/1.1\r\nHost: {DOMAIN}\r\nOrigin: {ORIGIN}\r\n'
                 'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
                 f'Sec-WebSocket-Key: {key}\r\nX-Forwarded-Proto: https\r\n\r\n').encode()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        deadline = time.monotonic() + 8
        connection.settimeout(5)
        connection.connect('/run/act.sock')
        connection.sendall(handshake)
        headers = bytearray()
        while not headers.endswith(b'\r\n\r\n'):
            require(len(headers) < 8192, 'WebSocket handshake headers exceed the bound.')
            headers.extend(recv_exact(connection, 1, deadline))
        lines = bytes(headers).decode('iso-8859-1').split('\r\n')
        require(lines[0].split(' ', 2)[1] == '101', 'WebSocket upgrade did not reach the tracking route.')
        fields = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
        fields = {k.lower(): v.strip() for k, v in fields.items()}
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        require(fields.get('sec-websocket-accept') == accept, 'WebSocket upgrade verification failed.')
        body = b'{"type":"viewer_auth"}'
        mask = os.urandom(4)
        connection.sendall(bytes([0x81, 0x80 | len(body)]) + mask + bytes(x ^ mask[i % 4] for i, x in enumerate(body)))
        opcode, payload = websocket_frame(connection, deadline)
        require(opcode == 1 and json.loads(payload) == {'type': 'auth_error'},
                'Anonymous tracking did not fail closed; response data was not retained.')
        opcode, payload = websocket_frame(connection, deadline)
        require(opcode == 8 and len(payload) >= 2 and struct.unpack('!H', payload[:2])[0] == 4403,
                'Anonymous tracking did not close with the authorization refusal.')


def run(arguments, *, timeout=30, env=None, input=None):
    # The helper and its owned command group survive terminal HUP. On timeout
    # or an explicit INT/TERM, kill that owned group before recovery so a late
    # runuser/Node client cannot submit another PM2 prepare after cleanup.
    args = [str(item) for item in arguments]
    with subprocess.Popen(args, stdin=subprocess.DEVNULL if input is None else subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=SYSTEM_ENV if env is None else env, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(input=input, timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


class Activation:
    def __init__(self, record):
        self.record = Path(record)
        self.work = None
        self.phase = 'preflight'
        self.sequence = 0
        self.backend_attempted = False
        self.backend_healthy = False
        self.frontend_attempted = False
        self.frontend_started = False
        self.dump_attempted = False
        self.route_attempted = False
        self.reload_attempted = False
        self.activated = False
        self.candidate_identity = None
        self.dump_new_hash = None

    def receipt(self, state):
        require(self.work is not None, 'Private activation journal is not available.')
        private_write(self.work / (state + '.json'), json_bytes({
            'state': state, 'phase': self.phase,
            'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'backend_sha': BACKEND_SHA, 'frontend_sha': FRONTEND_SHA,
            'backend_readiness_passed': self.backend_healthy,
            'public_activation_complete': state == 'ACTIVATED',
            'full_journey_acceptance': False, 'real_phone_gps_started_by_helper': False,
        }))

    def command(self, label, arguments, *, timeout=30, env=None, input=None, log=True):
        result = run(arguments, timeout=timeout, env=env, input=input)
        if log and self.work:
            self.sequence += 1
            private_write(self.work / f'{self.sequence:03d}-{label}.log', result.stdout + result.stderr)
        require(result.returncode == 0, label + ' failed; inspect the private activation record.')
        return result.stdout

    def git(self, *arguments):
        # Keep the root operator's existing Git trust configuration, as staging
        # did; do not change global safe.directory or repository settings.
        environment = os.environ.copy()
        environment['GIT_TERMINAL_PROMPT'] = '0'
        return self.command('git-source-read', ['/usr/bin/git', '-C', REPO, *arguments], env=environment, log=False)

    def source_matches(self, root, revision, subtree, files):
        for relative in files:
            require(regular_bytes(root / relative) == self.git('show', f'{revision}:{subtree}/{relative}'),
                    'A staged source or dependency file has drifted from the reviewed commit.')

    def unit(self, name):
        raw = self.command('unit-state', ['/usr/bin/systemctl', 'show', name, '--no-pager',
                           '-p', 'ActiveState', '-p', 'MainPID', '-p', 'WorkingDirectory'], log=False)
        result = dict(line.split('=', 1) for line in raw.decode().splitlines() if '=' in line)
        require(result.get('ActiveState') == 'active' and int(result.get('MainPID', '0')) > 1,
                'A required application service is not active.')
        return result

    def pm2_rows(self):
        require((PM2_HOME / 'rpc.sock').is_socket(), 'Existing PM2 daemon socket is unavailable; no daemon is started.')
        pid = int((PM2_HOME / 'pm2.pid').read_text().strip())
        require(pid > 1, 'PM2 daemon PID is invalid.')
        os.kill(pid, 0)
        if hasattr(self, 'daemon_pid'):
            require(pid == self.daemon_pid, 'The PM2 daemon changed during activation.')
        else:
            self.daemon_pid = pid
        output = self.command('pm2-read', ['/usr/sbin/runuser', '-u', 'act', '--', NODE,
                             '-e', PM2_READ_ONLY, PM2_ROOT, PM2_HOME / 'rpc.sock'],
                              env=act_env(), timeout=20, log=False)
        rows = json.loads(output)
        require(isinstance(rows, list), 'PM2 returned an unexpected process list.')
        return rows

    def require_retained(self, rows, with_candidate=False):
        require(len(rows) == len(self.retained) + int(with_candidate), 'PM2 process inventory drifted.')
        for identity in self.retained:
            row = one(rows, identity['name'])
            require(pm2_identity(row) == identity, 'A retained frontend process or environment changed.')
            require(Path(f'/proc/{row["pid"]}/cwd').resolve(strict=True) == Path(row['pm2_env']['pm_cwd']),
                    'A retained frontend process directory changed.')

    def require_common(self, expected_site_hash):
        require(SITE.resolve(strict=True) == self.site and sha(regular_bytes(self.site)) == expected_site_hash
                and regular_bytes(MASTER) == self.master and sorted(SITE.parent.iterdir()) == self.entries,
                'Nginx master/site or enabled-site linkage drifted.')
        for name, baseline in self.unchanged_units.items():
            require(self.unit(name) == baseline, 'An unrelated service changed during activation.')
        require(sha((BACK_ROOT / 'shared/.env').read_bytes()) == self.plan['backend']['shared_environment_sha256'],
                'Shared backend configuration changed after staging.')

    def http(self, target, path, nonce=False):
        require(path.startswith('/') and '\r' not in path and '\n' not in path, 'Unsafe readiness path.')
        if nonce:
            path += ('&' if '?' in path else '?') + 'act_release_check=' + self.work.name
        arguments = ['/usr/bin/curl', '--silent', '--show-error', '--noproxy', '*',
                     '--connect-timeout', '3', '--max-time', '8', '--max-filesize', '16777216',
                     '-H', 'Accept-Encoding: identity', '-H', 'Cache-Control: no-cache',
                     '-H', 'X-Forwarded-Proto: https', '-w', '\n%{http_code}']
        if target in ('3002', '3003'):
            arguments += ['-H', 'Host: ' + DOMAIN, 'http://127.0.0.1:' + target + path]
        elif target == 'backend':
            arguments += ['--unix-socket', '/run/act.sock', '-H', 'Host: ' + DOMAIN, 'http://localhost' + path]
        elif target == 'origin':
            # Only the loopback-pinned origin may use its origin certificate.
            arguments += ['--insecure', '--resolve', DOMAIN + ':443:127.0.0.1', ORIGIN + path]
        elif target == 'public':
            arguments += [ORIGIN + path]  # Normal public certificate verification.
        else:
            raise Stop('Unknown readiness destination.')
        result = self.command('http-readiness', arguments, timeout=12, log=False)
        body, code = result.rsplit(b'\n', 1)
        return int(code), body

    def nginx(self, label, *args):
        return self.command(label, ['/usr/sbin/nginx', *args], timeout=30)

    def preflight(self):
        require(os.geteuid() == 0, 'Use the approved root Hostinger session.')
        require(self.record.parent == BACKUP_ROOT, 'Unexpected staging parent directory.')
        private_path(self.record, directory=True)
        require(self.record.resolve(strict=True) == self.record, 'Staging record path resolves through a symlink.')
        private_path(self.record / 'plan.json')
        self.plan = json.loads((self.record / 'plan.json').read_bytes())
        validate_plan(self.record, self.plan)
        require(not list(self.record.glob('activation-*')),
                'A prior activation journal exists; inspect its final status instead of rerunning.')
        self.work = Path(tempfile.mkdtemp(prefix='activation-', dir=self.record))
        self.receipt('STARTED')
        say('PRIVATE_ACTIVATION_RECORD=' + str(self.work))
        self.backend = Path(self.plan['backend_release'])
        self.frontend = Path(self.plan['frontend_release'])
        self.assets = Path(self.plan['public_assets'])
        self.name = self.plan['candidate_pm2_name']
        for path in (self.backend, self.frontend, self.assets):
            require(path.is_dir() and path.resolve(strict=True) == path, 'A staged release directory is missing or symlinked.')
        require(CURRENT.is_symlink() and CURRENT.resolve(strict=True) == BACK_OLD,
                'Current backend no longer matches the staged preimage.')
        self.current_link = os.readlink(CURRENT)
        private_write(self.work / 'backend-current-before.json', json_bytes({'link': self.current_link, 'resolved': str(BACK_OLD)}))
        require(json.loads(regular_bytes(BACK_OLD / 'release.json')).get('git_sha') == BACK_BASE,
                'Previous backend release receipt differs.')
        require(json.loads(regular_bytes(self.backend / 'release.json')) == self.plan['backend'],
                'Staged backend release receipt changed.')
        require(sha(regular_bytes(self.backend / 'apps/trips/consumers.py')) == CONSUMER_HASH,
                'Staged tracking consumer is not the tested source.')
        for root in (BACK_OLD, self.backend):
            require((root / '.venv').resolve(strict=True) == VENV, 'The fixed Python environment provider changed.')
            for relative in ('.env', 'media', 'static', 'logs'):
                require((root / relative).resolve(strict=True) == (BACK_ROOT / 'shared' / relative).resolve(strict=True),
                        'A shared backend resource arrangement changed.')
        require(sha((BACK_ROOT / 'shared/.env').read_bytes()) == self.plan['backend']['shared_environment_sha256'],
                'Shared backend environment changed after staging.')
        require(sha(regular_bytes(self.backend / 'requirements.txt')) == self.plan['backend']['requirements_sha256']
                and regular_bytes(self.backend / 'requirements.txt') == regular_bytes(VENV.parent / 'requirements.txt'),
                'Backend dependency requirements changed.')
        self.source_matches(self.backend, BACKEND_SHA, 'act_backend-main',
                            ['apps/trips/consumers.py', 'requirements.txt', 'myProject/settings/base.py', 'myProject/asgi.py', 'apps/trips/routing.py'])
        self.source_matches(self.frontend, FRONTEND_SHA, 'act_website-main',
                            [*FRONT_FILES, 'package.json', 'package-lock.json', 'next.config.ts'])
        require(sha(regular_bytes(FRONT_OLD / '.next/BUILD_ID')) == FRONT_BUILD_HASH,
                'Serving frontend build changed after staging.')
        self.build_id = regular_bytes(self.frontend / '.next/BUILD_ID').decode().strip().encode()
        require(self.build_id.decode() == self.plan['frontend_build_id'] and
                sha(regular_bytes(self.frontend / 'package-lock.json')) == self.plan['frontend_lock_sha256'],
                'Staged frontend build/dependency identity changed.')
        for relative in ENV_NAMES:
            old, new = FRONT_OLD / relative, self.frontend / relative
            require(old.exists() == new.exists() and (not old.exists() or old.read_bytes() == regular_bytes(new)),
                    'Frontend environment files changed after staging.')
        private_path(Path(self.plan['private_public_environment_file']))
        self.public = json.loads(Path(self.plan['private_public_environment_file']).read_bytes())
        public_environment(self.public)
        self.phase = 'capture current process and routing preimages'
        self.backend_before = self.unit('act.service')
        require(self.backend_before.get('WorkingDirectory') == str(CURRENT) and
                Path('/proc/' + self.backend_before['MainPID'] + '/cwd').resolve(strict=True) == BACK_OLD,
                'The backend service is not using the recorded current release.')
        self.unchanged_units = {name: self.unit(name) for name in UNCHANGED_UNITS}
        enabled = self.command('pm2-startup-state', ['/usr/bin/systemctl', 'is-enabled', 'pm2-act.service'], log=False)
        require(enabled.strip() == b'enabled', 'The existing PM2 startup unit is not enabled.')
        rows = self.pm2_rows()
        require(len(rows) == len(RETAINED) and {p.get('name') for p in rows} == set(RETAINED),
                'PM2 inventory changed; additional processes will not be omitted or touched.')
        for name, identity in self.plan['retained_pm2_identities'].items():
            row = one(rows, name)
            observed = {'pid': row['pid'], 'pm_id': row['pm_id'],
                        **{key: row['pm2_env'].get(key) for key in ('pm_cwd', 'pm_exec_path', 'exec_interpreter', 'args')}}
            require(observed == identity and row['pm2_env'].get('status') == 'online',
                    'Retained frontend no longer matches the staging identity.')
        self.retained = [pm2_identity(one(rows, name)) for name in RETAINED]
        self.require_retained(rows)
        private_write(self.work / 'pm2-processes-before.json', json_bytes(rows))
        self.dump_before = regular_bytes(DUMP)
        self.saved_before = json.loads(self.dump_before)
        require(isinstance(self.saved_before, list) and len(self.saved_before) == len(RETAINED),
                'PM2 saved inventory differs; existing definitions are preserved.')
        for row in rows:
            saved_matches_live(one(self.saved_before, row['name']), row)
        private_write(self.work / 'dump.pm2.before', self.dump_before)
        if (PM2_HOME / 'dump.pm2.bak').exists():
            private_write(self.work / 'dump.pm2.bak.before', regular_bytes(PM2_HOME / 'dump.pm2.bak'))
        # Reuse the existing daemon installation; importing its API may not create missing infrastructure.
        for relative in ('logs', 'pids', 'modules'):
            require((PM2_HOME / relative).is_dir(), 'Existing PM2 runtime directory is missing.')
        require((PM2_HOME / 'module_conf.json').is_file(), 'Existing PM2 module configuration is missing.')
        old_env = one(rows, 'act-preview-892317f')['pm2_env']
        overrides = {key: value for key, value in old_env.items() if key.startswith('NEXT_PUBLIC_') and isinstance(value, str)}
        overrides.update({key: value for key, value in old_env.get('env', {}).items()
                          if key.startswith('NEXT_PUBLIC_') and isinstance(value, str)})
        effective = json.loads(self.command('public-environment-resolution', [NODE, '-e', NODE_ENV_READ, FRONT_OLD],
                                           env=act_env() | overrides, log=False))
        require(effective == self.public, 'The effective public environment changed after the connected build.')
        require(not self.command('candidate-port-check', ['ss', '-H', '-ltn', 'sport = :3003'], log=False).strip(),
                'The proposed loopback port 3003 is occupied; no process touched.')
        self.site = Path(self.plan['live_site_resolved'])
        require(self.site.is_absolute() and self.site.is_relative_to(Path('/etc/nginx')) and
                SITE.resolve(strict=True) == self.site and not self.site.is_symlink(), 'Nginx site target differs.')
        self.original = regular_bytes(self.record / 'original.conf')
        self.candidate = regular_bytes(self.record / 'candidate.conf')
        self.rollback = regular_bytes(self.record / 'rollback-with-assets.conf')
        for name, data in (('original', self.original), ('candidate', self.candidate), ('rollback', self.rollback)):
            require(sha(data) == self.plan[name + '_sha256'], 'A staged Nginx file checksum differs.')
        require(route_pair(self.original, self.assets) == (self.candidate, self.rollback),
                'Staged candidate changes more than the reviewed frontend routes/assets.')
        self.old_hash, self.new_hash, self.rollback_hash = sha(self.original), sha(self.candidate), sha(self.rollback)
        self.master = regular_bytes(MASTER)
        self.entries = sorted(SITE.parent.iterdir())
        require(all(path.is_file() for path in self.entries), 'An enabled Nginx site entry is not a file.')
        for name, data in (('original', self.original), ('candidate', self.candidate), ('rollback-with-assets', self.rollback)):
            private_write(self.work / (name + '.conf'), data)
        private_write(self.work / 'nginx-master-before.conf', self.master)
        self.effective_before = self.nginx('nginx-effective-before', '-T')
        for variant in ('candidate', 'rollback-with-assets'):
            path = self.work / (variant + '-validation.conf')
            private_write(path, validation_master(self.master, self.entries, self.work / (variant + '.conf')))
            self.nginx('validate-' + variant, '-t', '-c', path, '-p', '/etc/nginx/')
        manifest = regular_bytes(self.record / 'assets-manifest.json')
        require(sha(manifest) == self.plan['asset_manifest_sha256'], 'Staged static manifest changed.')
        self.asset_map = json.loads(manifest)
        require(isinstance(self.asset_map, dict) and self.asset_map, 'Staged asset manifest is empty.')
        for relative, expected in self.asset_map.items():
            path = PurePosixPath(relative)
            require(not path.is_absolute() and '..' not in path.parts and re.fullmatch('[0-9a-f]{64}', expected),
                    'Unsafe staged public asset path.')
            asset = self.assets / relative
            require(asset.resolve(strict=True) == asset and sha(regular_bytes(asset)) == expected,
                    'A staged public asset changed.')
        self.phase = 'readiness baseline'
        self.page = '/en'
        code, body = self.http('3002', self.page)
        require(code == 200, 'Retained frontend did not pass its existing page readiness check.')
        self.old_paths = html_assets(body)
        require(self.old_paths, 'Retained frontend page lacks identifiable build assets.')
        for target in ('origin', 'public'):
            code, body = self.http(target, self.page, True)
            require(code == 200 and html_assets(body) == self.old_paths,
                    'Existing website routing does not match the retained frontend build.')
        self.api_code, _ = self.http('backend', API_PATH)
        require(self.api_code in (401, 403), 'Existing protected backend route did not require authentication.')
        for target in ('origin', 'public'):
            code, _ = self.http(target, API_PATH, True)
            require(code == self.api_code, 'Existing public API routing differs from the protected backend route.')
        self.require_common(self.old_hash)
        self.require_retained(self.pm2_rows())
        require(regular_bytes(DUMP) == self.dump_before and self.unit('act.service') == self.backend_before,
                'A backend/PM2 preimage changed during preflight.')
        require(self.nginx('nginx-effective-recheck', '-T') == self.effective_before,
                'Effective Nginx configuration changed during preflight.')
        self.receipt('PREFLIGHT_PASSED')
        say('STAGED PAIR AND RECOVERY PREIMAGES VERIFIED')

    def check_backend(self, target):
        deadline = time.monotonic() + 40
        for attempt in range(5):
            try:
                require(CURRENT.is_symlink() and CURRENT.resolve(strict=True) == target, 'Backend current target differs.')
                state = self.unit('act.service')
                require(state.get('WorkingDirectory') == str(CURRENT) and
                        Path('/proc/' + state['MainPID'] + '/cwd').resolve(strict=True) == target,
                        'The restarted backend is not using the selected source.')
                code, _ = self.http('backend', API_PATH)
                require(code == self.api_code, 'The protected backend route changed its authentication status.')
                if target == self.backend:
                    require(sha(regular_bytes(target / 'apps/trips/consumers.py')) == CONSUMER_HASH,
                            'Running backend consumer source differs.')
                    anonymous_refusal()
                self.backend_after = state
                return
            except (Stop, OSError, ValueError, subprocess.TimeoutExpired):
                if attempt == 4 or time.monotonic() >= deadline:
                    raise Stop('Bounded backend readiness failed; GPS testing remains blocked.')
                time.sleep(2)

    def pm2_payload(self):
        return {'socket': str(PM2_HOME / 'rpc.sock'), 'pid_file': str(PM2_HOME / 'pm2.pid'),
                'daemon_pid': self.daemon_pid, 'retained': self.retained,
                'identity_fields': [*LAUNCH_FIELDS, 'status', 'restart_time', 'pm_uptime']}

    def candidate_row(self, rows):
        self.require_retained(rows, with_candidate=True)
        row = one(rows, self.name)
        env = row['pm2_env']
        require(row['pid'] > 1 and env.get('status') == 'online'
                and env.get('pm_cwd') == str(self.frontend)
                and env.get('pm_exec_path') == str(self.frontend / 'node_modules/next/dist/bin/next')
                and env.get('exec_interpreter') == str(NODE) and env.get('args') == ARGS
                and env.get('exec_mode') == 'fork_mode'
                and all(env.get(key) == value for key, value in POLICY.items()), 'New frontend process definition differs.')
        require(Path(f'/proc/{row["pid"]}/cwd').resolve(strict=True) == self.frontend,
                'New frontend process directory differs.')
        effective = env.get('env', {})
        require(effective.get('NODE_ENV') == 'production' and effective.get('ACT_TRACKING_ACTIVATION') == self.work.name and
                all(effective.get(key) == value for key, value in self.public.items()),
                'New frontend did not retain the captured build environment.')
        return row

    def start_frontend(self):
        self.phase = 'start the new loopback frontend'
        self.require_common(self.old_hash)
        self.require_retained(self.pm2_rows())
        require(regular_bytes(DUMP) == self.dump_before, 'Saved PM2 preimage changed before candidate start.')
        self.receipt('FRONTEND_START_STARTED')
        self.frontend_attempted = True
        config = {'name': self.name, 'cwd': str(self.frontend),
                  'script': str(self.frontend / 'node_modules/next/dist/bin/next'),
                  'interpreter': str(NODE), 'args': ARGS, 'exec_mode': 'fork', 'instances': 1,
                  'watch': False, 'env': {'NODE_ENV': 'production', 'NEXT_TELEMETRY_DISABLED': '1',
                  'ACT_TRACKING_ACTIVATION': self.work.name, **self.public}, **POLICY}
        payload = self.pm2_payload() | {'config': config, 'policy': POLICY}
        self.command('pm2-start-candidate', ['/usr/sbin/runuser', '-u', 'act', '--', NODE, '-e', PM2_START, PM2_ROOT],
                     env=act_env(), input=json_bytes(payload), timeout=30)
        self.frontend_started = True
        for attempt in range(6):
            try:
                row = self.candidate_row(self.pm2_rows())
                code, body = self.http('3003', self.page)
                require(code == 200, 'New frontend HTTP readiness failed.')
                self.new_paths = html_assets(body)
                unique = sorted(self.new_paths - self.old_paths)
                require(self.new_paths and (self.build_id in body or unique), 'New frontend identity is not distinguishable.')
                self.marker = ('asset', unique[0]) if unique else ('build', self.build_id)
                old_code, old_body = self.http('3002', self.page)
                require(old_code == 200 and not self.matches_new(old_body), 'Retained/new build identities are ambiguous.')
                self.candidate_identity = pm2_identity(row)
                self.check_assets = set()
                for paths in (self.old_paths, self.new_paths):
                    for extension in ('.js', '.css'):
                        choices = sorted(path for path in paths if path.endswith(extension))
                        require(choices, 'An expected page JavaScript/CSS asset is absent.')
                        self.check_assets.add(choices[0])
                require(all(path.removeprefix('/_next/static/') in self.asset_map for path in self.check_assets),
                        'A referenced old/new asset is absent from the staged union.')
                return
            except (Stop, OSError, ValueError, subprocess.TimeoutExpired):
                if attempt == 5:
                    raise Stop('Bounded new frontend readiness failed.')
                time.sleep(2)

    def persist_frontend(self):
        self.phase = 'persist the new frontend without replacing retained definitions'
        row = self.candidate_row(self.pm2_rows())
        require(pm2_identity(row) == self.candidate_identity, 'New frontend restarted before its startup definition could be saved.')
        require(regular_bytes(DUMP) == self.dump_before, 'Saved PM2 state changed; persistence refused.')
        # PM2's Startup.js dump/resurrect format is pm2_env with these transient
        # fields removed. Preserve existing saved rows exactly as parsed, adding
        # only this process; do not rewrite old environments from live values.
        new_saved = copy.deepcopy(row['pm2_env'])
        for key in ('instances', 'pm_id', 'prev_restart_delay', '_tree_pids'):
            new_saved.pop(key, None)
        require(not new_saved.get('pmx_module') and new_saved.get('name') == self.name,
                'Candidate is not a normal PM2 application definition.')
        self.dump_new = json_bytes([*self.saved_before, new_saved])
        self.dump_new_hash = sha(self.dump_new)
        private_write(self.work / 'dump.pm2.candidate', self.dump_new)
        self.receipt('PM2_PERSIST_STARTED')
        self.dump_attempted = True
        atomic_site(DUMP, self.dump_new, sha(self.dump_before))
        saved = json.loads(regular_bytes(DUMP))
        require(saved[:-1] == self.saved_before and saved[-1] == new_saved,
                'Saved startup process list did not preserve the retained definitions.')
        saved_matches_live(saved[-1], row)
        self.require_retained(self.pm2_rows(), with_candidate=True)
        self.receipt('FRONTEND_READY_AND_PERSISTED')

    def matches_new(self, body):
        kind, marker = self.marker
        return marker in body if kind == 'build' else marker in html_assets(body)

    def check_frontend_routes(self, new):
        expected = self.new_paths if new else self.old_paths
        for target in ('origin', 'public'):
            code, body = self.http(target, self.page, True)
            require(code == 200 and html_assets(body) == expected and self.matches_new(body) == new,
                    'Website routing did not serve the selected frontend build.')
            for asset in sorted(self.check_assets):
                code, content = self.http(target, quote(asset, safe='/._-'), True)
                require(code == 200 and sha(content) == self.asset_map[asset.removeprefix('/_next/static/')],
                        'An old/new website JavaScript or CSS asset did not match its recorded bytes.')
            code, _ = self.http(target, API_PATH, True)
            require(code == self.api_code, 'Protected API routing changed its authentication status.')

    def reload(self):
        self.command('nginx-reload', ['/usr/bin/systemctl', 'reload', 'nginx.service'], timeout=30)

    def switch_routing(self):
        self.phase = 'install the reviewed frontend routing'
        self.require_common(self.old_hash)
        require(self.nginx('nginx-final-preimage', '-T') == self.effective_before,
                'Effective Nginx configuration changed before the public switch.')
        self.candidate_row(self.pm2_rows())
        require(sha(regular_bytes(DUMP)) == self.dump_new_hash, 'Saved startup state changed before public routing.')
        self.receipt('ROUTING_CHANGE_STARTED')
        self.route_attempted = True
        atomic_site(self.site, self.candidate, self.old_hash)
        self.nginx('nginx-installed-candidate', '-t')
        self.phase = 'reload and verify public routing'
        self.receipt('NGINX_RELOAD_STARTED')
        self.reload_attempted = True
        self.reload()
        for attempt in range(3):
            try:
                self.check_frontend_routes(True)
                return
            except (Stop, OSError, ValueError, subprocess.TimeoutExpired):
                if attempt == 2:
                    raise Stop('Bounded public website readiness failed.')
                time.sleep(2)

    def activate(self):
        self.phase = 'switch and restart the tracking backend'
        self.require_common(self.old_hash)
        self.require_retained(self.pm2_rows())
        require(self.unit('act.service') == self.backend_before and regular_bytes(DUMP) == self.dump_before,
                'Activation preimages changed before the backend switch.')
        self.receipt('BACKEND_SWITCH_STARTED')
        self.backend_attempted = True
        atomic_current(self.backend, BACK_OLD)
        self.command('backend-restart', ['/usr/bin/systemctl', 'restart', 'act.service'], timeout=45)
        self.check_backend(self.backend)
        self.backend_healthy = True
        self.receipt('AUTHENTICATED_BACKEND_READY')
        say('AUTHENTICATED BACKEND READY; PHONE GPS TEST HAS NOT STARTED')
        self.start_frontend()
        self.persist_frontend()
        self.switch_routing()
        self.phase = 'final deployed-pair receipt'
        self.require_common(self.new_hash)
        self.candidate_row(self.pm2_rows())
        require(self.unit('act.service') == self.backend_after and CURRENT.resolve(strict=True) == self.backend,
                'Backend identity changed during the frontend cutover.')
        require(sha(regular_bytes(DUMP)) == self.dump_new_hash, 'PM2 persistence changed during cutover.')
        self.receipt('ACTIVATED')
        self.activated = True
        say('TRACKING BACKEND AND WEBSITE ACTIVATED - JOURNEY ACCEPTANCE NOT YET RUN')
        say('BACKEND_SHA=' + BACKEND_SHA)
        say('FRONTEND_SHA=' + FRONTEND_SHA)
        say('PRIVATE_ACTIVATION_RECORD=' + str(self.work))

    def remove_new_frontend(self):
        payload = self.pm2_payload() | {'name': self.name, 'cwd': str(self.frontend),
                   'script': str(self.frontend / 'node_modules/next/dist/bin/next'),
                   'interpreter': str(NODE), 'args': ARGS, 'activation_nonce': self.work.name,
                   'allow_absent': self.frontend_started}
        self.command('pm2-remove-only-new-candidate', ['/usr/sbin/runuser', '-u', 'act', '--', NODE,
                     '-e', PM2_REMOVE_CANDIDATE, PM2_ROOT], env=act_env(), input=json_bytes(payload), timeout=30)
        self.require_retained(self.pm2_rows())

    def restore_dump(self):
        if not self.dump_attempted:
            require(regular_bytes(DUMP) == self.dump_before, 'Saved PM2 state drifted; recovery will not overwrite it.')
            return
        current_hash = sha(regular_bytes(DUMP))
        require(current_hash in (sha(self.dump_before), self.dump_new_hash),
                'Saved PM2 state changed concurrently; recovery will not overwrite it.')
        if current_hash != sha(self.dump_before):
            atomic_site(DUMP, self.dump_before, self.dump_new_hash)
        require(regular_bytes(DUMP) == self.dump_before, 'Prior PM2 startup state was not restored.')

    def recover(self):
        if self.activated:
            return
        if not self.backend_attempted:
            if self.work:
                self.receipt('STOPPED_BEFORE_ACTIVATION')
            say('STOP: No live activation was attempted. Inspect the private record before any retry.')
            return
        self.phase = 'recover only the changes made by this activation'
        if not self.backend_healthy:
            # Frontend cannot have started before backend readiness. No phone GPS
            # was sent by this helper; old authorization is not accepted for GPS.
            require(not self.frontend_attempted and not self.route_attempted,
                    'Unexpected recovery ordering; backend rollback withheld.')
            require(CURRENT.is_symlink(), 'Backend pointer is no longer a symlink; recovery withheld.')
            target = CURRENT.resolve(strict=True)
            require(target in (self.backend, BACK_OLD), 'Concurrent backend switch; recovery withheld.')
            if target == self.backend:
                atomic_current(BACK_OLD, self.backend)
                self.command('backend-restore-restart', ['/usr/bin/systemctl', 'restart', 'act.service'], timeout=45)
            self.check_backend(BACK_OLD)
            self.receipt('BACKEND_ROLLED_BACK_GPS_BLOCKED')
            say('BACKEND ACTIVATION FAILED - PREVIOUS BACKEND RESTORED; GPS TEST REMAINS BLOCKED')
            return
        # Once the new auth consumer is ready, a website failure never restores
        # the old anonymous consumer. Preserve the healthy secure backend.
        if not self.route_attempted:
            self.require_common(self.old_hash)
        if self.route_attempted:
            require(SITE.resolve(strict=True) == self.site and regular_bytes(MASTER) == self.master
                    and sorted(SITE.parent.iterdir()) == self.entries, 'Nginx linkage/master drift; automatic routing recovery withheld.')
            observed = sha(regular_bytes(self.site))
            allowed = (self.new_hash, self.rollback_hash) if self.reload_attempted else (self.old_hash, self.new_hash)
            require(observed in allowed, 'Concurrent Nginx edit; automatic recovery will not overwrite it.')
            if self.reload_attempted:
                if observed != self.rollback_hash:
                    atomic_site(self.site, self.rollback, self.new_hash)
                self.nginx('nginx-rollback-with-assets', '-t')
                self.reload()
                self.check_frontend_routes(False)
            elif observed != self.old_hash:
                atomic_site(self.site, self.original, self.new_hash)
                self.nginx('nginx-original-restored', '-t')
        # Remove only the exact new candidate after traffic is back on 3002.
        # Restoring the dump first protects boot persistence even if cleanup fails.
        if self.frontend_attempted:
            self.restore_dump()
            self.remove_new_frontend()
        require(CURRENT.resolve(strict=True) == self.backend, 'New secure backend pointer changed during frontend recovery.')
        self.check_backend(self.backend)
        self.receipt('FRONTEND_ROLLED_BACK_AUTHENTICATED_BACKEND_RETAINED')
        say('FRONTEND ACTIVATION FAILED - PREVIOUS WEBSITE RETAINED; AUTHENTICATED BACKEND PRESERVED')
        say('PHONE GPS TEST REMAINS BLOCKED PENDING THE COORDINATED WEBSITE RELEASE')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true', required=True,
                        help='Use only after owner approval of the exact backend/website pair.')
    parser.add_argument('--record', required=True, type=Path,
                        help='Existing root-private tracking-stage directory from the successful staging receipt.')
    arguments = parser.parse_args(argv)
    require(os.geteuid() == 0, 'Use the approved root Hostinger session.')
    os.umask(0o077)
    os.chdir('/tmp')
    operation = Activation(arguments.record)
    # The browser terminal may disconnect. Continue the bounded transaction and
    # durable receipts; INT/TERM request recovery while HUP/output loss do not.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    def interrupted(_signum, _frame):
        raise Stop('Operator interrupted activation.')
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        with Path('/run/lock/act-backend-deploy.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                operation.preflight()
                operation.activate()
                return 0
            except (Exception, KeyboardInterrupt) as error:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                reason = str(error) if isinstance(error, Stop) else type(error).__name__
                say('STOP [' + operation.phase + ']: ' + reason)
                try:
                    operation.recover()
                except (Exception, KeyboardInterrupt) as recovery_error:
                    if operation.work:
                        try:
                            operation.receipt('RECOVERY_INCOMPLETE')
                        except Exception:
                            pass
                    say('STOP: Recovery is incomplete. Do not rerun activation, restart all services or restore a database.')
                if operation.work:
                    say('PRIVATE_ACTIVATION_RECORD=' + str(operation.work))
                return 1
    except BlockingIOError:
        say('STOP: Another release operation holds the deployment lock. No activation attempted.')
        return 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Stop as error:
        say('STOP: ' + str(error))
        raise SystemExit(1)
