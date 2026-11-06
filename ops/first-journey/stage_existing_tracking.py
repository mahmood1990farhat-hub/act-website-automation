#!/usr/bin/env python3
"""Prepare ACT tracking releases and a routing plan; never activate them.

Only --prepare with two exact reviewed Git SHAs is supported. Existing releases,
PM2 process definitions/dump, current symlink and live Nginx files are read only.
No Django import, migration, provider probe, booking request or service control.
The existing source clone may receive exact commit objects; no checkout, branch
ref, working-tree file or FETCH_HEAD is changed.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import grp
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit

REPO = Path('/var/www/atg/front-end/airportandcitytransfer_repo')
BACK_ROOT = Path('/var/www/atg/atg-backend')
CURRENT = BACK_ROOT / 'current'
BACK_BASE = '82c0b14ad2a71e1ce3d8d1df3527431b698ac461'
BACK_OLD = BACK_ROOT / 'releases/20261016T-ready-82c0b14/backend'
VENV = BACK_ROOT / 'releases/20261015T-ready-735c966/backend/.venv'
FRONT_ROOT = Path('/var/www/atg/front-end')
FRONT_OLD = FRONT_ROOT / 'releases/20261015-892317f'
FRONT_BASE = '892317fcf938fad5fa6cd9a833a79e900dcc4d8f'
FRONT_BUILD_HASH = '7e829c27388c892d02e4ba3846d1aa84ede880796fb67348fe0d39f106aa5e4a'
OLD_ASSETS = FRONT_ROOT / 'act-static-892317f-cutover'
OLD_PLAN = Path('/root/act-release-backup/cutover-dydysjlc/frontend-switch-892317f')
OLD_RECEIPT = OLD_PLAN / 'activation-z9391_cw/ACTIVATED.json'
SITE = Path('/etc/nginx/sites-enabled/airportandcitytransfer')
MASTER = Path('/etc/nginx/nginx.conf')
NODE_DIR = Path('/home/act/.nvm/versions/node/v24.13.0/bin')
NODE = NODE_DIR / 'node'
NPM = NODE_DIR / 'npm'
PM2 = Path('/home/act/.nvm/versions/node/v24.13.0/lib/node_modules/pm2/bin/pm2')
ORIGIN = 'https://airportandcitytransfer.com'
ENV_NAMES = ('.env.production.local', '.env.local', '.env.production', '.env')
FRONT_ALLOWED = {
    'src/lib/trip-tracking-url.ts',
    'src/hooks/use-trip-tracking.ts',
    'src/components/_components/dashboard/tracking/trip-tracking-provider.tsx',
    'src/components/_components/dashboard/tracking/trip-tracking-map.tsx',
    'src/components/_components/dashboard/TripsDashboard.tsx',
    'src/components/_components/Trips/MyTripsCard.tsx',
}
BACK_TEST_FILES = {
    'apps/trips/tests/test_tracking_access.py',
    'apps/trips/tests/tracking_test_urls.py',
    'myProject/settings/tracking_tests.py',
}
STATUS = {'phase': 'preflight', 'record': None}


def phase(name):
    STATUS['phase'] = name


class Stop(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    require(path.is_file() and not path.is_symlink(), 'Expected regular file is missing or symlinked.')
    return digest(path.read_bytes())


def private_write(path, data):
    with path.open('xb') as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(data)


def json_write(path, data):
    private_write(path, (json.dumps(data, indent=2, sort_keys=True) + '\n').encode())


def run(arguments, label, *, cwd=None, env=None, timeout=30, log=None):
    try:
        result = subprocess.run([str(x) for x in arguments], cwd=cwd, env=env,
                                stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Stop(label + ' could not complete; serving releases were not activated.') from exc
    if log is not None:
        private_write(log, result.stdout + result.stderr)
    require(result.returncode == 0, label + ' failed; no output containing configuration is printed.')
    return result.stdout


def git(*arguments):
    environment = os.environ.copy()
    environment['GIT_TERMINAL_PROMPT'] = '0'
    return run(['git', '-C', REPO, *arguments], 'Git source operation', env=environment, timeout=120)


def verify_remote(value):
    value = value.strip()
    if value.startswith('git@github.com:'):
        path = value[len('git@github.com:'):]
    else:
        parsed = urlsplit(value)
        require(parsed.scheme in ('https', 'ssh') and parsed.hostname == 'github.com'
                and not parsed.query and not parsed.fragment, 'Existing source remote is not the expected GitHub repository.')
        path = parsed.path.lstrip('/')
    require(path.removesuffix('.git') == 'mahmood1990farhat-hub/act-website-automation',
            'Existing source remote is not the expected ACT repository.')


def verify_diff(base, candidate, subtree, allowed):
    changed = git('diff', '--name-only', base, candidate, '--', subtree).decode().splitlines()
    runtime = []
    for path in changed:
        relative = path.removeprefix(subtree + '/')
        if relative.startswith('tests/') or relative.startswith('docs/'):
            continue
        if subtree == 'act_backend-main' and relative in BACK_TEST_FILES:
            continue
        require(relative in allowed, 'Candidate changes a production file outside the reviewed tracking scope.')
        runtime.append(relative)
    require(runtime, 'Candidate has no reviewed tracking application change.')
    return sorted(runtime)


def export_subtree(sha, subtree, destination):
    require(not destination.exists() and not destination.is_symlink(), 'New release destination already exists; preserved.')
    data = git('archive', '--format=tar', sha, subtree)
    destination.mkdir(mode=0o750)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for member in archive.getmembers():
            parts = PurePosixPath(member.name).parts
            require(parts and parts[0] == subtree and '..' not in parts and not member.name.startswith('/'),
                    'Unsafe source archive path; staging stopped.')
            require(member.isdir() or member.isfile(), 'Source archive contains a link or special file; staging stopped.')
            if len(parts) == 1:
                continue
            path = destination.joinpath(*parts[1:])
            if member.isdir():
                path.mkdir(mode=0o750, parents=True, exist_ok=True)
            else:
                path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                require(stream is not None, 'Source file could not be read.')
                with path.open('xb') as output:
                    shutil.copyfileobj(stream, output)
                path.chmod(0o750 if member.mode & 0o111 else 0o640)


def source_matches(root, sha, subtree, paths):
    for path in paths:
        expected = git('show', f'{sha}:{subtree}/{path}')
        current = root / path
        require(current.is_file() and not current.is_symlink() and current.read_bytes() == expected,
                'A recorded deployed source or dependency file has drifted; current files preserved.')


def ownership(root, uid, gid, directory_mode=None):
    for current, directories, files in os.walk(root, followlinks=False):
        os.chown(current, uid, gid, follow_symlinks=False)
        if directory_mode is not None:
            os.chmod(current, directory_mode, follow_symlinks=False)
        for name in directories + files:
            os.chown(Path(current) / name, uid, gid, follow_symlinks=False)


def act_env():
    return {'HOME': '/home/act', 'USER': 'act', 'LOGNAME': 'act', 'PM2_HOME': '/home/act/.pm2',
            'PATH': str(NODE_DIR) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8',
            'NODE_ENV': 'production', 'NEXT_TELEMETRY_DISABLED': '1'}


PM2_READ_ONLY = r'''
// PM2's documented source protocol: axon req + rpc.Client, getMonitorData.
// Load only transport libraries, never PM2's CLI/API daemon-launch functions.
const fs=require('fs'), path=require('path'), root=process.argv[1], socket=process.argv[2];
function dependency(name) {
  const bundled=path.join(root,'modules',name);
  return fs.existsSync(bundled) ? require(bundled) : require(require.resolve(name,{paths:[root]}));
}
const axon=dependency('pm2-axon'), rpc=dependency('pm2-axon-rpc');
const request=axon.socket('req'), client=new rpc.Client(request);
const deadline=setTimeout(()=>process.exit(2),15000);
request.once('error',()=>process.exit(2));
request.once('connect',()=>client.call('getMonitorData',{},(error,rows)=>{
  if(error || !Array.isArray(rows)) return process.exit(2);
  clearTimeout(deadline); request.close();
  process.stdout.write(JSON.stringify(rows),()=>process.exit(0));
}));
request.connect(socket);
'''


def pm2_snapshot():
    require(Path('/home/act/.pm2/rpc.sock').is_socket(), 'Existing act PM2 daemon is unavailable; no daemon started.')
    daemon_pid = int(Path('/home/act/.pm2/pm2.pid').read_text().strip())
    os.kill(daemon_pid, 0)
    rows = json.loads(run(['/usr/sbin/runuser', '-u', 'act', '--', NODE, '-e', PM2_READ_ONLY,
                           PM2.parent.parent, '/home/act/.pm2/rpc.sock'],
                          'Read existing PM2 metadata through passive local RPC', env=act_env()))
    selected = {}
    public_overrides = {}
    for name in ('act', 'act-preview-892317f'):
        matches = [item for item in rows if item.get('name') == name]
        require(len(matches) == 1, 'Required PM2 identity is missing or duplicated; nothing restarted.')
        item = matches[0]
        settings = item['pm2_env']
        require(settings.get('status') == 'online' and item.get('pid', 0) > 1, 'A retained frontend is not online.')
        selected[name] = {'pid': item['pid'], 'pm_id': item['pm_id'],
                          **{key: settings.get(key) for key in ('pm_cwd', 'pm_exec_path', 'exec_interpreter', 'args')}}
        if name == 'act-preview-892317f':
            require(settings.get('pm_cwd') == str(FRONT_OLD)
                    and settings.get('pm_exec_path') == str(FRONT_OLD / 'node_modules/next/dist/bin/next')
                    and settings.get('exec_interpreter') == str(NODE)
                    and settings.get('args') == ['start', '--hostname', '127.0.0.1', '--port', '3002'],
                    'Serving frontend launch definition differs from the recorded release.')
            require(Path(f'/proc/{item["pid"]}/cwd').resolve(strict=True) == FRONT_OLD,
                    'Serving frontend process directory differs.')
            for key, value in settings.items():
                if key.startswith('NEXT_PUBLIC_') and isinstance(value, str):
                    public_overrides[key] = value
            for key, value in settings.get('env', {}).items():
                if key.startswith('NEXT_PUBLIC_') and isinstance(value, str):
                    public_overrides[key] = value
    return selected, public_overrides


NODE_ENV_READ = r'''
const root=process.argv[1], silent={info(){},warn(){},error(){}};
const e=require(require.resolve('@next/env',{paths:[root]})).loadEnvConfig(root,false,silent,true).combinedEnv;
process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(e).filter(([k,v])=>k.startsWith('NEXT_PUBLIC_') && typeof v==='string'))));
'''


def validate_public_environment(values):
    require(values.get('NEXT_PUBLIC_API_BASE_URL') == ORIGIN,
            'Existing frontend configuration must select the exact ACT API origin without an /api suffix.')
    stripe = values.get('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY', '')
    require(bool(re.fullmatch(r'pk_test_[A-Za-z0-9]{16,}', stripe)), 'Existing Stripe public configuration is not recognised as test mode.')
    maps = values.get('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY', '')
    require(bool(maps.strip()) and not re.search(r'placeholder|synthetic|replace|your[_ -]?key', maps, re.I),
            'Existing Maps configuration is missing or a placeholder.')


BACK_ENV_READ = r'''
import environ,json,sys
e=environ.Env(); environ.Env.read_env(sys.argv[1])
print(json.dumps({'firebase':e('FIREBASE_CREDENTIALS_PATH',default='airport-city-transfer-33ac7-firebase-adminsdk-fbsvc-aba3144ea6.json'),
 'private_root':e('ACT_DRIVER_PRIVATE_UPLOAD_ROOT',default=''), 'ni_key_present':bool(e('ACT_NI_ENCRYPTION_KEY',default=''))}))
'''


def prepare_backend(destination, sha, www_gid):
    export_subtree(sha, 'act_backend-main', destination)
    require(not (destination / '.venv').exists(), 'Source unexpectedly contains a virtual environment.')
    for name in ('.env', 'media', 'static', 'logs'):
        source = BACK_OLD / name
        expected = BACK_ROOT / 'shared' / name
        require(source.exists() and source.resolve(strict=True) == expected.resolve(strict=True),
                'An existing shared backend resource does not match its recorded arrangement.')
        target = destination / name
        if target.exists():
            require(not target.is_symlink(), 'Unexpected source resource link.')
            if name == 'static':
                target.rename(destination / 'static.staged')
            elif target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.symlink_to(expected)
    (destination / '.venv').symlink_to(VENV)
    configured = json.loads(run([VENV / 'bin/python', '-B', '-c', BACK_ENV_READ, BACK_OLD / '.env'],
                                'Read required backend resource paths', env={'PATH':'/usr/bin:/bin'}))
    private_root = Path(configured.get('private_root', ''))
    require(private_root.is_absolute() and private_root.is_dir() and configured.get('ni_key_present'),
            'Existing private driver storage or NI encryption configuration is incomplete; values are not printed.')
    require(not private_root.resolve().is_relative_to((BACK_ROOT / 'shared/media').resolve()),
            'Private evidence must not be placed under shared public media.')
    firebase = Path(configured['firebase'])
    require('..' not in firebase.parts and bool(str(firebase)), 'Unexpected Firebase credential path.')
    source = firebase if firebase.is_absolute() else BACK_OLD / firebase
    require(source.is_file(), 'Existing Firebase credential file is missing; no replacement generated.')
    copied_credential = None
    if not firebase.is_absolute():
        target = destination / firebase
        require(not target.exists() and not target.is_symlink(), 'Credential destination unexpectedly exists in Git source.')
        target.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_credential = (target, source.stat())
    ownership(destination, 0, www_gid, directory_mode=0o750)
    if copied_credential:
        target, info = copied_credential
        os.chown(target, info.st_uid, info.st_gid)
        os.chmod(target, stat.S_IMODE(info.st_mode))
    run([VENV / 'bin/python', '-B', '-c',
         'import ast,sys; ast.parse(open(sys.argv[1]).read())', destination / 'apps/trips/consumers.py'],
        'Compile tracking consumer without importing the application', env={'PATH':'/usr/bin:/bin'})
    return {'git_sha': sha, 'state': 'STAGED_NOT_ACTIVE', 'venv_provider': str(VENV),
            'requirements_sha256': digest_file(destination / 'requirements.txt'),
            'consumer_sha256': digest_file(destination / 'apps/trips/consumers.py'),
            'shared_environment_sha256': digest((BACK_OLD / '.env').read_bytes()),
            'firebase_sha256': digest(source.read_bytes()),
            'private_driver_storage_preserved': True, 'firebase_arrangement_preserved': True}


def route_pair(original, assets):
    text = original.decode()
    port = re.compile(r'(?m)^([ \t]*proxy_pass[ \t]+)http://127\.0\.0\.1:3002([ \t]*;)')
    alias = re.compile(r'(?m)^([ \t]*alias[ \t]+)' + re.escape(str(OLD_ASSETS)) + r'/([ \t]*;)')
    require(len(port.findall(text)) == 3 and len(alias.findall(text)) == 1,
            'Existing routing differs from the recorded three upstreams and static alias; no route guessed.')
    rollback = alias.sub(lambda match: match[1] + str(assets) + '/' + match[2], text)
    candidate = port.sub(lambda match: match[1] + 'http://127.0.0.1:3003' + match[2], rollback)
    return candidate.encode(), rollback.encode()


# Reused unchanged from prepare_act_frontend_switch.py (83bef405...):
def validation_master(original, entries, candidate):
    pattern = re.compile(r'(?m)^[ \t]*include[ \t]+/etc/nginx/sites-enabled/\*[ \t]*;')
    require(len(pattern.findall(original)) == 1, 'Master configuration uses an unexpected site include; nothing activated.')
    require(sum(path == SITE for path in entries) == 1, 'Expected enabled ACT site not found exactly once.')
    lines = []
    for path in entries:
        value = str(candidate if path == SITE else path)
        require(not any(c in value for c in ('"', '\\', '\n', '\r', '$')), 'Unusual include path; manual review required.')
        lines.append('    include "' + value + '";')
    configured = pattern.sub(lambda _: '\n'.join(lines), original)
    # nginx -t may create/open its pid file even though it starts no server.
    # Keep validation away from the live pid file as well as the live config.
    pid_pattern = re.compile(r'(?m)^[ \t]*pid[ \t]+[^;\n]+;')
    require(len(pid_pattern.findall(configured)) <= 1, 'Ambiguous PID configuration; validation refused.')
    private_pid = 'pid "' + str(candidate.parent / 'nginx-validation.pid') + '";'
    if pid_pattern.search(configured):
        configured = pid_pattern.sub(lambda _: private_pid, configured)
    else:
        configured = private_pid + '\n' + configured
    return configured


def copy_assets(roots, destination):
    """Copy only public Next static files; keep old hashes for already-open pages.

    Never follow symlinks, overwrite a collision, or modify either source build.
    """
    require(not destination.exists() and not destination.is_symlink(), 'Asset staging directory already exists; preserved.')
    destination.mkdir(mode=0o755)
    destination.chmod(0o755)
    manifest = {}
    for root in roots:
        require(root.is_dir() and not root.is_symlink(), 'Expected public static source directory missing or symlinked.')
        count = 0
        for current, dirs, files in os.walk(root, followlinks=False):
            for name in sorted(dirs):
                source = Path(current) / name
                require(not source.is_symlink(), 'Symlink inside public static assets; no secrets followed.')
                target = destination / source.relative_to(root)
                target.mkdir(mode=0o755, exist_ok=True)
                target.chmod(0o755)
            for name in sorted(files):
                source = Path(current) / name
                require(stat.S_ISREG(source.lstat().st_mode), 'Non-regular public asset found; nothing followed.')
                relative = str(source.relative_to(root))
                value = digest_file(source)
                if relative in manifest:
                    require(manifest[relative] == value, 'Different content shares an old/new asset path; both builds preserved.')
                else:
                    target = destination / relative
                    with source.open('rb') as incoming, target.open('xb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                        os.fchmod(outgoing.fileno(), 0o644)
                    require(digest_file(target) == value, 'An asset changed while copying; candidate not accepted.')
                    manifest[relative] = value
                count += 1
        require(count > 0, 'A source static directory was empty; candidate not accepted.')
    return dict(sorted(manifest.items()))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True)
    parser.add_argument('--backend-sha', required=True)
    parser.add_argument('--frontend-sha', required=True)
    args = parser.parse_args()
    require(os.geteuid() == 0, 'Use the existing root Hostinger terminal for this inactive staging operation.')
    require(all(re.fullmatch(r'[0-9a-f]{40}', value) for value in (args.backend_sha,args.frontend_sha)),
            'Both candidates require exact lowercase 40-character commit SHAs.')
    os.umask(0o077)
    with Path('/run/lock/act-backend-deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage(args.backend_sha, args.frontend_sha)


def stage(backend_sha, frontend_sha):
    phase('verify recorded existing release identities')
    require(CURRENT.is_symlink() and CURRENT.resolve(strict=True) == BACK_OLD,
            'Current backend differs from the recorded 82c0b14 release.')
    require(json.loads((BACK_OLD/'release.json').read_text()).get('git_sha') == BACK_BASE,
            'Current backend release receipt differs.')
    require((BACK_OLD/'.venv').resolve(strict=True) == VENV and (VENV/'bin/python').is_file(),
            'Existing fixed Python environment provider differs.')
    require(digest_file(FRONT_OLD/'.next/BUILD_ID') == FRONT_BUILD_HASH, 'Serving frontend build identity differs.')
    require(NODE.is_file() and NPM.is_file() and PM2.is_file(), 'Recorded Node/npm/PM2 installation is unavailable.')
    require(REPO.is_dir(), 'Existing ACT source clone is missing; no clone location guessed.')
    verify_remote(git('remote','get-url','origin').decode())
    pm2_before, overrides = pm2_snapshot()  # One passive local RPC read; cannot spawn a daemon.
    listeners = run(['ss','-H','-ltn','sport = :3003'], 'Check only proposed candidate port')
    require(not listeners.strip(), 'Proposed loopback port 3003 is occupied; no process touched.')
    phase('read existing routing and activation records')
    previous_plan = json.loads((OLD_PLAN/'plan.json').read_text())
    previous_receipt = json.loads(OLD_RECEIPT.read_text())
    require(previous_receipt.get('state') == 'ACTIVATED'
            and previous_receipt.get('backend_sha') == BACK_BASE
            and previous_receipt.get('frontend_sha') == FRONT_BASE, 'Prior activation receipt differs.')
    site_target = SITE.resolve(strict=True)
    require(str(site_target) == previous_plan.get('live_site_resolved') and site_target.is_relative_to(Path('/etc/nginx'))
            and not site_target.is_symlink(), 'Enabled Nginx site target differs.')
    original, master = site_target.read_bytes(), MASTER.read_bytes()
    require(digest(original) == previous_plan.get('candidate_sha256'), 'Live Nginx site changed since the recorded activation.')
    require(previous_plan.get('public_assets') == str(OLD_ASSETS), 'Recorded static union differs.')
    old_manifest_bytes = (OLD_PLAN/'assets-manifest.json').read_bytes()
    require(digest(old_manifest_bytes) == previous_plan.get('asset_manifest_sha256'), 'Prior asset manifest changed.')
    old_manifest = json.loads(old_manifest_bytes)
    for relative, expected in old_manifest.items():
        path = PurePosixPath(relative)
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe existing asset manifest path.')
        require(digest_file(OLD_ASSETS/relative) == expected, 'Retained asset union differs from its manifest.')
    phase('retrieve exact candidate source objects')
    for sha in (backend_sha, frontend_sha):
        git('fetch','--no-write-fetch-head','--no-tags','origin',sha)
        require(git('rev-parse',sha+'^{commit}').decode().strip() == sha, 'Candidate Git identity differs.')
    git('merge-base','--is-ancestor',BACK_BASE,backend_sha)
    git('merge-base','--is-ancestor',FRONT_BASE,frontend_sha)
    back_files = verify_diff(BACK_BASE,backend_sha,'act_backend-main',{'apps/trips/consumers.py'})
    front_files = verify_diff(FRONT_BASE,frontend_sha,'act_website-main',FRONT_ALLOWED)
    source_matches(BACK_OLD,BACK_BASE,'act_backend-main',['requirements.txt','myProject/settings/base.py','apps/trips/consumers.py'])
    require((VENV.parent/'requirements.txt').read_bytes() == (BACK_OLD/'requirements.txt').read_bytes(),
            'Preserved Python environment provider has different dependency requirements.')
    source_matches(FRONT_OLD,FRONT_BASE,'act_website-main',
                   sorted(FRONT_ALLOWED - {'src/lib/trip-tracking-url.ts'}) +
                   ['package.json','package-lock.json','next.config.ts'])
    require(not (FRONT_OLD/'src/lib/trip-tracking-url.ts').exists()
            and not (FRONT_OLD/'src/lib/trip-tracking-url.ts').is_symlink(),
            'The serving release contains an unrecorded tracking URL helper; preserve and review it.')
    phase('resolve the existing frontend configuration privately')
    env_source_hashes = {}
    for name in ENV_NAMES:
        source = FRONT_OLD/name
        if source.exists():
            require(source.is_file(), 'Unexpected frontend environment file type.')
            env_source_hashes[name] = digest(source.read_bytes())
    require(env_source_hashes or overrides, 'Existing frontend configuration was not found; no values guessed.')
    combined_env = act_env() | overrides
    public = json.loads(run([NODE,'-e',NODE_ENV_READ,FRONT_OLD], 'Resolve existing frontend configuration privately', env=combined_env))
    validate_public_environment(public)
    backup_root = Path('/root/act-release-backup')
    require(backup_root.is_dir(), 'Existing private recovery root is missing.')
    record = Path(tempfile.mkdtemp(prefix='tracking-stage-',dir=backup_root))
    STATUS['record'] = record
    json_write(record/'STARTED.json',{'state':'STAGING_STARTED','backend_sha':backend_sha,'frontend_sha':frontend_sha})
    print('PRIVATE_STAGING_RECORD='+str(record),flush=True)
    tag = record.name.removeprefix('tracking-stage-')
    backend = BACK_ROOT/'releases'/f'20261106-tracking-{backend_sha[:7]}-{tag}'/'backend'
    frontend = FRONT_ROOT/'releases'/f'20261106-tracking-{frontend_sha[:7]}-{tag}'
    assets = FRONT_ROOT/f'act-static-tracking-{frontend_sha[:7]}-{tag}'
    backend.parent.mkdir(mode=0o750)
    backend.parent.chmod(0o750)
    www_gid = grp.getgrnam('www-data').gr_gid
    os.chown(backend.parent,0,www_gid)
    print('Preparing separate backend and frontend releases; current services remain untouched.', flush=True)
    phase('prepare new backend runtime without importing the application')
    back_receipt = prepare_backend(backend,backend_sha,www_gid)
    json_write(backend/'release.json',back_receipt)
    phase('prepare new frontend source and private configuration')
    export_subtree(frontend_sha,'act_website-main',frontend)
    frontend_source_hashes = {str(path.relative_to(frontend)): digest_file(path)
                             for path in frontend.rglob('*') if path.is_file()}
    for name in ENV_NAMES:
        destination = frontend/name
        require(not destination.exists() and not destination.is_symlink(), 'Candidate source unexpectedly contains a runtime environment file.')
        source = FRONT_OLD/name
        if name in env_source_hashes:
            private_write(destination,source.read_bytes())
    act = pwd.getpwnam('act')
    ownership(frontend,act.pw_uid,act.pw_gid)
    # Resolve public values once; keep them only in child environments/private envfiles.
    build_env = act_env() | public
    # Runtime launch must reuse these captured public overrides too. Keep values
    # in a root-private file, never in console output or a shared report.
    json_write(record/'frontend-public-environment.json',public)
    build_env['npm_config_update_notifier'] = 'false'
    run(['/usr/sbin/runuser','-u','act','--',NPM,'ci','--include=dev','--ignore-scripts','--no-audit','--no-fund'],
        'Install unchanged locked frontend dependencies', cwd=frontend,env=build_env,timeout=300,log=record/'npm-ci.log')
    print('Building the connected frontend in its new release directory.',flush=True)
    phase('build new frontend')
    run(['/usr/sbin/runuser','-u','act','--',NODE,frontend/'node_modules/next/dist/bin/next','build'],
        'Build connected frontend',cwd=frontend,env=build_env,timeout=300,log=record/'frontend-build.log')
    require(digest_file(frontend/'package-lock.json') == digest_file(FRONT_OLD/'package-lock.json'), 'Build changed the dependency lock.')
    for relative, expected in frontend_source_hashes.items():
        require(digest_file(frontend/relative) == expected, 'Build changed a committed frontend source file.')
    build_id = (frontend/'.next/BUILD_ID').read_text().strip()
    require(bool(build_id), 'Frontend build identity is missing.')
    phase('prepare public asset union and inactive routing files')
    asset_manifest = copy_assets((OLD_ASSETS,frontend/'.next/static'),assets)
    candidate, rollback = route_pair(original,assets)
    private_write(record/'original.conf',original)
    private_write(record/'candidate.conf',candidate)
    private_write(record/'rollback-with-assets.conf',rollback)
    entries = sorted(SITE.parent.iterdir())
    require(all(path.is_file() for path in entries),'Unexpected enabled Nginx site entry.')
    for name in ('candidate','rollback-with-assets'):
        validation = validation_master(master.decode(),entries,record/(name+'.conf'))
        config = record/(name+'-validation.conf')
        private_write(config,validation.encode())
        run(['/usr/sbin/nginx','-t','-c',config,'-p','/etc/nginx/'],
            'Validate inactive Nginx '+name,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'},log=record/(name+'-validation.log'))
    phase('verify unchanged current release and live routing')
    require(CURRENT.resolve(strict=True) == BACK_OLD and SITE.resolve(strict=True) == site_target
            and site_target.read_bytes() == original and MASTER.read_bytes() == master,
            'Existing release or routing changed concurrently; prepared candidate must not be activated.')
    require(digest((BACK_OLD/'.env').read_bytes()) == back_receipt['shared_environment_sha256'],
            'Shared backend configuration changed during staging.')
    for name, expected in env_source_hashes.items():
        require(digest((FRONT_OLD/name).read_bytes()) == expected, 'Existing frontend configuration changed during build.')
    for identity in pm2_before.values():
        require(Path(f'/proc/{identity["pid"]}/cwd').resolve(strict=True) == Path(identity['pm_cwd']),
                'A retained frontend process changed during staging.')
    json_write(record/'assets-manifest.json',asset_manifest)
    plan = {'state':'STAGED_NOT_ACTIVE','backend_sha':backend_sha,'frontend_sha':frontend_sha,
      'backend_release':str(backend),'frontend_release':str(frontend),'backend':back_receipt,
      'frontend_build_id':build_id,'frontend_lock_sha256':digest_file(frontend/'package-lock.json'),
      'frontend_changed_application_files':front_files,'backend_changed_application_files':back_files,
      'api_origin':ORIGIN,'stripe_public_mode':'test','maps_key_present':True,
      'environment_resolution':'existing production envfiles plus captured public PM2 overrides; no secret values printed',
      'build_network_isolation':False,'provider_or_booking_probes_executed':False,
      'git_object_cache_updated':True,'git_checkout_or_refs_changed':False,
      'candidate_listener_started':False,'candidate_upstream':'127.0.0.1:3003','prior_upstream':'127.0.0.1:3002',
      'candidate_pm2_name':'act-tracking-'+frontend_sha[:7],
      'private_public_environment_file':str(record/'frontend-public-environment.json'),
      'pm2_launch':{'cwd':str(frontend),'script':str(frontend/'node_modules/next/dist/bin/next'),'interpreter':str(NODE),
                   'args':['start','--hostname','127.0.0.1','--port','3003'],'env':{'NODE_ENV':'production'}},
      'retained_pm2_identities':pm2_before,'live_site':str(SITE),'live_site_resolved':str(site_target),
      'original_sha256':digest(original),'candidate_sha256':digest(candidate),'rollback_sha256':digest(rollback),
      'public_assets':str(assets),'asset_manifest_sha256':digest_file(record/'assets-manifest.json'),
      'nginx_validation_passed':True,'approval_required':'Separate exact-pair approval before any activation, process start or live switch.'}
    json_write(record/'plan.json',plan)
    print('TRACKING RELEASES BUILT AND ROUTING PREPARED - NOT ACTIVATED')
    print('BACKEND_SHA='+backend_sha)
    print('FRONTEND_SHA='+frontend_sha)
    print('PRIVATE_STAGING_RECORD='+str(record))
    print('No application listeners started, services controlled, live routing changed or bookings submitted.')


if __name__ == '__main__':
    try:
        main()
    except (Stop,OSError,ValueError,KeyError,tarfile.TarError) as error:
        # Never include arbitrary exception text: parsers/commands can contain credentials.
        message = str(error) if isinstance(error,Stop) else 'Required existing metadata or runtime input could not be read; no activation was attempted.'
        if STATUS['record'] is not None:
            try:
                json_write(STATUS['record']/'FAILED.json',{'state':'STAGING_INCOMPLETE_NOT_ACTIVATED',
                    'phase':STATUS['phase'],'error_type':type(error).__name__,'reason':message,
                    'partial_candidates_retained':True})
            except OSError:
                pass
        print('STOP ['+STATUS['phase']+'; '+type(error).__name__+']: '+message)
        raise SystemExit(1)
