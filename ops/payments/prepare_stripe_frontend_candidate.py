#!/usr/bin/env python3
"""ACT frontend Stripe test-key repair: read-only check / INACTIVE build only.

Never changes existing services, running release, Nginx, PM2, backend or keys.
--prepare is an explicit separate operator step and stages an immutable build.
Activation requires a different, separately approved, audited procedure.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tarfile

FRONT_SHA = '02e59f95b5fd85d6ad07e881f3f2671a01a7bd65'
BACK_SHA = 'd77e896af9daca5a39b7a85d5b76c5821e008d23'
ACCOUNT = 'acct_1RDnQjBxjYEaMc5N'
INTENT = 'pi_3UcqTQBxjYEaMc5N09dbf1zh'
FRONT_ROOT = Path('/var/www/atg/front-end')
RELEASES = FRONT_ROOT / 'releases'
ACTIVE = RELEASES / 'passenger-02e59f9-eoszulb3'
OLD_ASSETS = FRONT_ROOT / 'act-static-passenger-02e59f9-eoszulb3'
CANDIDATE = RELEASES / 'stripe-pk-02e59f9-20261117'
NEW_ASSETS = FRONT_ROOT / 'act-static-stripe-pk-02e59f9-20261117'
SITE = Path('/etc/nginx/sites-enabled/airportandcitytransfer')
REPO = FRONT_ROOT / 'airportandcitytransfer_repo'
RECEIPT = Path('/root/act-release-backup/tracking-stage-oe9oh1vi/frontend-public-environment.json')
BACKEND = Path('/var/www/atg/atg-backend/releases/20261106-tracking-d77e896-oe9oh1vi/backend')
BACK_CURRENT = Path('/var/www/atg/atg-backend/current')
BACK_ENV = Path('/var/www/atg/atg-backend/shared/.env')
LOCK = Path('/run/lock/act-backend-deploy.lock')
RECORD = Path('/root/act-release-backup/stripe-frontend-pk-20261117')
NODE_DIR = Path('/home/act/.nvm/versions/node/v24.13.0/bin')
NODE, NPM = NODE_DIR / 'node', NODE_DIR / 'npm'
ENV_NAMES = ('.env.production.local', '.env.local', '.env.production', '.env')
KEY_PATTERN = re.compile(rb'pk_test_[A-Za-z0-9]{16,240}')
PUBLIC_PATTERN = re.compile(r'pk_test_[A-Za-z0-9]{16,240}\Z')


class Stop(Exception):
    """No secret or external error string may be included."""


def require(ok, code):
    if not ok:
        raise Stop(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def plain_file(path, max_size=65536):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and info.st_size <= max_size, 'SOURCE_FILE_NOT_REGULAR_OR_OVERSIZED')
    return path.read_bytes()


def command(args, *, cwd=None, env=None, timeout=30, input_bytes=None):
    result = subprocess.run([str(item) for item in args], cwd=cwd,
                            env=env, input=input_bytes, capture_output=True,
                            timeout=timeout)
    require(result.returncode == 0, 'GUARDED_COMMAND_FAILED')
    return result.stdout


def receipt():
    info = RECEIPT.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o077,
            'PUBLIC_CONFIGURATION_RECEIPT_NOT_PRIVATE')
    values = json.loads(plain_file(RECEIPT))
    require(isinstance(values, dict) and all(
        isinstance(k, str) and re.fullmatch(r'NEXT_PUBLIC_[A-Z0-9_]+', k)
        and isinstance(v, str) for k, v in values.items()), 'PUBLIC_CONFIGURATION_RECEIPT_INVALID')
    public = values.get('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY', '')
    require(PUBLIC_PATTERN.fullmatch(public) is not None, 'OLD_PUBLIC_KEY_NOT_TEST_MODE')
    require(values.get('NEXT_PUBLIC_API_BASE_URL') == 'https://airportandcitytransfer.com',
            'PUBLIC_API_BASE_DRIFT')
    return values


def js_keys(root):
    directory = root / '.next/static'
    require(directory.is_dir() and not directory.is_symlink(), 'COMPILED_STATIC_MISSING')
    found = set()
    files = list(directory.rglob('*.js'))
    require(files, 'COMPILED_JS_MISSING')
    for f in files:
        require(f.is_file() and not f.is_symlink(), 'UNEXPECTED_COMPILED_JS_LINK')
        found.update(KEY_PATTERN.findall(f.read_bytes()))
    return found


def local_state():
    require(os.geteuid() == 0, 'ROOT_OPERATOR_REQUIRED')
    require(ACTIVE.is_dir() and not ACTIVE.is_symlink()
            and OLD_ASSETS.is_dir() and not OLD_ASSETS.is_symlink(), 'ACTIVE_RELEASE_MISSING')
    resolved_site = SITE.resolve(strict=True)
    require(resolved_site.is_relative_to(Path('/etc/nginx')),
            'NGINX_SITE_OUTSIDE_CONFIG_ROOT')
    config = plain_file(resolved_site, 262144).decode('utf-8')
    require(len(re.findall(r'proxy_pass\s+http://127\.0\.0\.1:3004\s*;', config)) == 3,
            'EXPECTED_THREE_ACTIVE_FRONTEND_ROUTES')
    require('act-static-passenger-02e59f9-eoszulb3' in config,
            'ACTIVE_ASSET_ALIAS_DRIFT')
    listener = command(['/usr/bin/ss', '-H', '-ltnp', 'sport = :3004']).decode()
    pids = set(re.findall(r'pid=(\d+)', listener))
    require(len(pids) == 1, 'FRONTEND_PROCESS_UNVERIFIED')
    pid = next(iter(pids))
    require(Path('/proc/' + pid + '/cwd').resolve(strict=True) == ACTIVE,
            'ACTIVE_FRONTEND_PROCESS_DRIFT')
    require(BACK_CURRENT.is_symlink() and BACK_CURRENT.resolve(strict=True) == BACKEND,
            'BACKEND_RELEASE_DRIFT')
    require(json.loads(plain_file(BACKEND / 'release.json')).get('git_sha') == BACK_SHA,
            'BACKEND_SOURCE_DRIFT')
    require(REPO.is_dir() and not REPO.is_symlink(), 'SOURCE_REPOSITORY_MISSING')
    commit = command(['git', '-C', REPO, 'rev-parse', FRONT_SHA + '^{commit}']).decode().strip()
    require(commit == FRONT_SHA, 'PINNED_FRONTEND_SOURCE_UNAVAILABLE')
    active_build = plain_file(ACTIVE / '.next/BUILD_ID', 1024).decode().strip()
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', active_build) is not None,
            'ACTIVE_FRONTEND_BUILD_ID_INVALID')
    public = receipt()
    require(js_keys(ACTIVE) == {public['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'].encode()},
            'COMPILED_FRONTEND_KEY_DRIFT')
    require(OLD_ASSETS.exists() and not OLD_ASSETS.is_symlink(), 'ACTIVE_ASSETS_UNAVAILABLE')
    return {'nginx_sha256': sha(config.encode()), 'active_build_id': active_build,
            'backend_env_sha256': sha(plain_file(BACK_ENV, 262144)),
            'active_public': public, 'pid': int(pid)}


def read_verified_helper():
    source = Path('/root/act-stripe-readonly/replace_expired_test_key.py')
    require(sha(plain_file(source, 131072)) ==
            '6b412d93c7bd563901c9fe0b031c718b76671ba4e906e5144b00e6dc546b99fe',
            'BACKEND_TEST_KEY_HELPER_DRIFT')
    import importlib.util
    spec = importlib.util.spec_from_file_location('act_stripe_recovery_pinned', source)
    require(spec is not None and spec.loader is not None, 'BACKEND_HELPER_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_candidate(new_public, old_public, helper):
    require(PUBLIC_PATTERN.fullmatch(new_public) is not None and new_public != old_public,
            'REPLACEMENT_TEST_PUBLIC_KEY_REQUIRED')
    from urllib.parse import quote
    snap = helper.read_env()
    helper.service_snapshot(snap)
    backend_secret = helper.key_span(snap.data)[2]
    account_status, account = helper.stripe_response('/v1/account', backend_secret)
    require(account_status == 200 and account.get('id') == ACCOUNT,
            'BACKEND_STRIPE_ACCOUNT_NOT_VERIFIED')
    status, intent = helper.stripe_response('/v1/payment_intents/' + INTENT, backend_secret)
    require(status == 200 and intent.get('id') == INTENT
            and intent.get('livemode') is False and intent.get('status') == 'requires_payment_method'
            and intent.get('payment_method') is None and intent.get('amount_received') == 0,
            'EXISTING_TEST_INTENT_NOT_UNPAID')
    secret = intent.get('client_secret')
    require(isinstance(secret, str) and re.fullmatch(
        re.escape(INTENT) + r'_secret_[A-Za-z0-9]{8,240}', secret) is not None,
        'EXISTING_TEST_CLIENT_SECRET_INVALID')
    status, observed = helper.stripe_response(
        '/v1/payment_intents/' + INTENT + '?client_secret=' + quote(secret, safe=''), new_public)
    require(status == 200 and observed.get('id') == INTENT
            and observed.get('livemode') is False, 'REPLACEMENT_TEST_PUBLIC_KEY_NOT_VERIFIED')


def copy_archived_source(path):
    archive = command(['git', '-C', REPO, 'archive', '--format=tar', FRONT_SHA,
                       'act_website-main'], timeout=120)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as stream:
        for member in stream.getmembers():
            parts = PurePosixPath(member.name).parts
            require(parts and parts[0] == 'act_website-main' and '..' not in parts
                    and (member.isdir() or member.isfile()) and not member.issym(),
                    'SOURCE_ARCHIVE_UNSAFE')
            target = path.joinpath(*parts[1:])
            if member.isdir():
                target.mkdir(parents=True, mode=0o750, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, mode=0o750, exist_ok=True)
                with stream.extractfile(member) as source:
                    with target.open('xb') as output:
                        output.write(source.read())
                    target.chmod(0o640)


def copy_asset_union():
    NEW_ASSETS.mkdir(mode=0o755)
    NEW_ASSETS.chmod(0o755)
    for origin in (OLD_ASSETS, CANDIDATE / '.next/static'):
        for source in origin.rglob('*'):
            require(not source.is_symlink(), 'ASSET_SYMLINK_REFUSED')
            rel = source.relative_to(origin)
            target = NEW_ASSETS / rel
            if source.is_dir():
                target.mkdir(mode=0o755, parents=True, exist_ok=True)
                target.chmod(0o755)
            else:
                require(source.is_file(), 'ASSET_NOT_REGULAR')
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                target.parent.chmod(0o755)
                if target.exists():
                    require(sha(target.read_bytes()) == sha(source.read_bytes()),
                            'ASSET_COLLISION_CONTENT_MISMATCH')
                else:
                    shutil.copy2(source, target, follow_symlinks=False)
                    target.chmod(0o644)


def stage(key, baseline):
    require(not CANDIDATE.exists() and not CANDIDATE.is_symlink()
            and not NEW_ASSETS.exists() and not NEW_ASSETS.is_symlink()
            and not RECORD.exists() and not RECORD.is_symlink(),
            'CANDIDATE_ALREADY_EXISTS_STOP_NO_OVERWRITE')
    require(not command(['/usr/bin/ss', '-H', '-ltn', 'sport = :3005']).strip(),
            'FUTURE_CANDIDATE_PORT_IN_USE')
    import fcntl
    require(LOCK.is_file() and not LOCK.is_symlink(), 'RELEASE_LOCK_UNAVAILABLE')
    with LOCK.open('r+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop('ACTIVE_RELEASE_LOCK_PRESENT') from None
        require(local_state()['nginx_sha256'] == baseline['nginx_sha256'],
                'ACTIVE_ROUTING_CHANGED_NO_PREPARATION')
        # Do not alter running services. The following only creates NEW paths.
        RECORD.mkdir(mode=0o700)
        CANDIDATE.mkdir(mode=0o750)
        copy_archived_source(CANDIDATE)
        require(not any((CANDIDATE / name).exists() for name in ENV_NAMES),
                'SOURCE_CONTAINS_RUNTIME_ENV_FILE')
        for name in ENV_NAMES:
            f = ACTIVE / name
            if f.exists():
                require(not f.is_symlink(), 'ACTIVE_ENV_SYMLINK_REFUSED')
                (CANDIDATE / name).write_bytes(plain_file(f, 262144))
                (CANDIDATE / name).chmod(0o640)
        user = pwd.getpwnam('act')
        for current, dirs, files in os.walk(CANDIDATE):
            for p in (Path(current), *(Path(current) / f for f in files)):
                os.chown(p, user.pw_uid, user.pw_gid)
        env = {'PATH': str(NODE_DIR) + ':/usr/bin:/bin', 'HOME': '/home/act',
               'USER': 'act', 'LOGNAME': 'act', 'NODE_ENV': 'production',
               'NEXT_TELEMETRY_DISABLED': '1', 'npm_config_update_notifier': 'false',
               **baseline['active_public'], 'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY': key}
        # Private logs; no key, environment, or provider responses are printed.
        def build(args, timeout, label):
            log = RECORD / (label + '.log')
            proc = subprocess.run(['/usr/sbin/runuser', '-u', 'act', '--', *map(str, args)],
                                  cwd=CANDIDATE, env=env, capture_output=True, timeout=timeout)
            log.write_bytes(proc.stdout + proc.stderr)
            log.chmod(0o600)
            require(proc.returncode == 0, label.upper() + '_FAILED_PRIVATE_LOG_RETAINED')
        build([NPM, 'ci', '--include=dev', '--ignore-scripts', '--no-audit', '--no-fund'],
              300, 'npm-ci')
        build([NODE, CANDIDATE / 'node_modules/next/dist/bin/next', 'build'], 300, 'next-build')
        require(js_keys(CANDIDATE) == {key.encode()}, 'CANDIDATE_COMPILED_KEY_MISMATCH')
        new_id = plain_file(CANDIDATE / '.next/BUILD_ID', 1024).decode().strip()
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', new_id) is not None,
                'CANDIDATE_BUILD_ID_INVALID')
        copy_asset_union()
        after = local_state()
        require(all(after[k] == baseline[k] for k in ('nginx_sha256', 'active_build_id',
                    'backend_env_sha256', 'pid')), 'ACTIVE_SERVICE_DRIFT_DURING_PREPARE')
        info = {'status': 'PREPARED_NOT_ACTIVATED', 'source_sha': FRONT_SHA,
                'backend_sha': BACK_SHA, 'old_build_id': baseline['active_build_id'],
                'new_build_id': new_id, 'candidate': str(CANDIDATE),
                'candidate_assets': str(NEW_ASSETS), 'old_release': str(ACTIVE),
                'old_assets': str(OLD_ASSETS), 'nginx_sha256': baseline['nginx_sha256'],
                'backend_env_sha256': baseline['backend_env_sha256'],
                'old_public_key_sha256': sha(baseline['active_public']['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'].encode()),
                'new_public_key_sha256': sha(key.encode()),
                'activation_authorized': False, 'webhook_changed': False,
                'backend_changed': False, 'current_frontend_changed': False}
        p = RECORD / 'plan.json'
        with p.open('x') as output:
            json.dump(info, output, indent=2, sort_keys=True)
        p.chmod(0o600)
        print('FRONTEND_CANDIDATE_PREPARED_NOT_ACTIVATED')
        print('CANDIDATE_RECORD: ' + str(RECORD / 'plan.json'))
        print('NO_PM2_NGINX_BACKEND_CHANGE')


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop('EXPECTED_ONLY_CHECK_OR_PREPARE_NO_KEY_ARGUMENT')


def main(argv=None):
    try:
        parser = SafeParser(description='ACT read-only frontend check / inactive key rebuild')
        actions = parser.add_mutually_exclusive_group(required=True)
        actions.add_argument('--check', action='store_true')
        actions.add_argument('--prepare', action='store_true')
        args = parser.parse_args(argv)
        before = local_state()
        print('PASS: CURRENT_FRONTEND_SOURCE_AND_KEY_MATCH_RETAINED_RECEIPT')
        if args.check:
            print('NO_CHANGES')
            return 0
        require(sys.stdin.isatty() and sys.stderr.isatty(),
                'HIDDEN_OPERATOR_KEY_ENTRY_REQUIRES_TTY')
        key = getpass.getpass('ACT valid replacement TEST pk key (hidden): ')
        helper = read_verified_helper()
        verify_candidate(key, before['active_public']['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'], helper)
        print('PASS: REPLACEMENT_KEY_READ_ONLY_VERIFIED')
        stage(key, before)
        return 0
    except Stop as exc:
        print('STOPPED: ' + str(exc) + '; NO_ACTIVATION', file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        print('STOPPED: PREPARATION_UNAVAILABLE_PRIVATE_EVIDENCE_RETAINED; NO_ACTIVATION',
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
