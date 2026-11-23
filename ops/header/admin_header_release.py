#!/usr/bin/env python3
"""Approved ACT Admin-link release, preserving the running frontend configuration.

--check is read-only. --deploy performs the owner-approved, one-attempt frontend
build/switch. --status only reports the private journal; it never resumes work.
No backend restart, payment request, credential change or Git branch operation.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from urllib.parse import quote, urlsplit

sys.dont_write_bytecode = True
PATCH_SHA = '4c69a03b2e38636ed3ea54f6d3f1a8bf0ab1e0e7'
PRIOR = Path('/root/act-stripe-readonly/passenger_frontend_release.py')
PRIOR_HASH = '2c880f9e116dad51b5acf973f49b992dbe8c8af4fca1883bd8f718b440151254'
FRONT = Path('/var/www/atg/front-end')
ACTIVE = FRONT / 'releases/stripe-pk-02e59f9-20261117'
CANDIDATE = FRONT / 'releases/admin-header-4c69a03-20261123'
OLD_ASSETS = FRONT / 'act-static-stripe-pk-02e59f9-20261117'
NEW_ASSETS = FRONT / 'act-static-admin-header-4c69a03-20261123'
RECORD = Path('/root/act-release-backup/admin-header-4c69a03-20261123')
LOCK = Path('/run/lock/act-backend-deploy.lock')
SITE = Path('/etc/nginx/sites-enabled/airportandcitytransfer')
MASTER = Path('/etc/nginx/nginx.conf')
BACK_ROOT = Path('/var/www/atg/atg-backend')
NODE_DIR = Path('/home/act/.nvm/versions/node/v24.13.0/bin')
NODE, NPM = NODE_DIR / 'node', NODE_DIR / 'npm'
PM2_HOME = Path('/home/act/.pm2')
DUMP = PM2_HOME / 'dump.pm2'
NAME, PORT = 'act-admin-header-4c69a03', 3006
DOMAIN = 'airportandcitytransfer.com'
OLD_BUILD = 'nhzNjHZ3-jrJtY8-rHjVp'
SITE_HASH = '6821267a448cb32532eb04b1fcbe9bb1a202325d8f583566abf8b3a2ed72eb10'
MENU_BEFORE = {
    'en': '2f0b301b1f607e162321c6f4d911f6f503da130286728b465fa453562ea803b8',
    'ar': 'd87bf013da744564cb81ded97843d8df6d7704f14ed80bfea4004bddceeed7f9',
}
MENU_AFTER = {
    'en': 'a6d114637a04bd19c6c5e040ec0aa8a39d14e96754a028fb697cb0e7d04898b5',
    'ar': '74d793c730338dae888c65fe3dcf5323f8249e661ea5fc3c05fa494898ec64f8',
}
LABELS = {'en': 'Admin', 'ar': 'الإدارة'}
EXCLUDED_DIRS = {'.next', 'node_modules', '.git'}
GENERATED = {'next-env.d.ts', 'tsconfig.tsbuildinfo'}
KEY_PATTERN = re.compile(rb'pk_(?:test|live)_[A-Za-z0-9]{16,240}')
SYSTEM_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}


class Stop(Exception):
    """Only fixed, non-secret status codes belong in this exception."""


def need(ok, code):
    if not ok:
        raise Stop(code)


def emit(message):
    # A lost Hostinger terminal must not interrupt an already journalled switch.
    try:
        print(message, flush=True)
    except (BrokenPipeError, OSError):
        pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'REGULAR_FILE_REQUIRED')
    return path.read_bytes()


def packed(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def write_new(path, data, mode=0o600):
    with path.open('xb') as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_prior():
    need(digest(regular(PRIOR)) == PRIOR_HASH, 'PINNED_RELEASE_UTILITIES_DIFFER')
    spec = importlib.util.spec_from_file_location('act_header_prior_utilities', PRIOR)
    need(spec is not None and spec.loader is not None, 'RELEASE_UTILITIES_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def patch_menu(raw, locale):
    need(locale in LABELS and digest(raw) == MENU_BEFORE[locale], 'MENU_PREIMAGE_DRIFT')
    needle = ('        "url": "/' + locale + '/download-app",\n'
              '        "protected": false\n      },\n').encode()
    insertion = ('      {\n        "name": "' + LABELS[locale] + '",\n'
                 '        "url": "/' + locale + '/admin",\n'
                 '        "protected": false\n      },\n').encode()
    need(raw.count(needle) == 1, 'MENU_INSERTION_AMBIGUOUS')
    result = raw.replace(needle, needle + insertion, 1)
    need(digest(result) == MENU_AFTER[locale], 'MENU_RESULT_DIFFERS_FROM_APPROVED_COMMIT')
    before, after = json.loads(raw), json.loads(result)
    links = after['navbar']['navLinks']
    index = next(i for i, item in enumerate(links) if item['url'] == f'/{locale}/admin')
    need(links.pop(index) == {'name': LABELS[locale], 'url': f'/{locale}/admin', 'protected': False}
         and after == before, 'UNRELATED_DICTIONARY_CHANGE')
    return result


def route_pair(original):
    text = original.decode()
    ports = re.compile(r'(?m)^([ \t]*proxy_pass[ \t]+)http://127\.0\.0\.1:3005([ \t]*;)')
    aliases = re.compile(r'(?m)^([ \t]*alias[ \t]+)' + re.escape(str(OLD_ASSETS)) + r'/([ \t]*;)')
    need(len(ports.findall(text)) == 3 and len(aliases.findall(text)) == 1,
         'EXPECTED_THREE_UPSTREAMS_AND_ONE_ASSET_ALIAS')
    rollback = aliases.sub(lambda m: m[1] + str(NEW_ASSETS) + '/' + m[2], text)
    proposed = ports.sub(lambda m: m[1] + f'http://127.0.0.1:{PORT}' + m[2], rollback)
    return proposed.encode(), rollback.encode()


def compiled_keys(root):
    static_root = root / '.next/static'
    need(static_root.is_dir() and not static_root.is_symlink(), 'COMPILED_ASSETS_MISSING')
    found, files = set(), 0
    for directory, dirs, names in os.walk(static_root, followlinks=False):
        for name in dirs + names:
            need(not (Path(directory) / name).is_symlink(), 'COMPILED_ASSET_LINK_REFUSED')
        for name in names:
            if name.endswith('.js'):
                files += 1
                found.update(KEY_PATTERN.findall(regular(Path(directory) / name)))
    need(files > 0, 'COMPILED_JAVASCRIPT_MISSING')
    return found


def extract_public_overrides(row):
    settings = row['pm2_env']
    values = {}
    for source in (settings, settings.get('env', {})):
        need(isinstance(source, dict), 'PM2_ENVIRONMENT_MALFORMED')
        for key, value in source.items():
            if key.startswith('NEXT_PUBLIC_'):
                need(re.fullmatch(r'NEXT_PUBLIC_[A-Z0-9_]+', key) and isinstance(value, str),
                     'PUBLIC_ENVIRONMENT_MALFORMED')
                need(key not in values or values[key] == value, 'PUBLIC_ENVIRONMENT_OVERRIDE_CONFLICT')
                values[key] = value
    return values


def validate_public(public, keys):
    need(isinstance(public, dict) and all(isinstance(k, str) and re.fullmatch(r'NEXT_PUBLIC_[A-Z0-9_]+', k)
         and isinstance(v, str) for k, v in public.items()), 'PUBLIC_ENVIRONMENT_MALFORMED')
    value = public.get('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY', '')
    need(re.fullmatch(r'pk_test_[A-Za-z0-9]{16,240}', value) is not None,
         'CURRENT_STRIPE_PUBLIC_KEY_NOT_TEST_MODE')
    need(keys == {value.encode()}, 'CURRENT_PUBLIC_KEY_DOES_NOT_MATCH_COMPILED_BUNDLE')
    need(public.get('NEXT_PUBLIC_API_BASE_URL') == 'https://' + DOMAIN, 'PUBLIC_API_ORIGIN_DRIFT')
    return public


def source_tree(root):
    need(root.is_dir() and root.resolve(strict=True) == root, 'SOURCE_DIRECTORY_INVALID')
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        if Path(directory) == root:
            dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
            files = [name for name in files if name not in GENERATED]
        for name in dirs + files:
            need(not (Path(directory) / name).is_symlink(), 'SOURCE_LINK_REFUSED')
        for name in files:
            path = Path(directory) / name
            result[str(path.relative_to(root))] = digest(regular(path))
    need(bool(result), 'SOURCE_TREE_EMPTY')
    return dict(sorted(result.items()))


def copy_source(source, target):
    need(not target.exists() and not target.is_symlink(), 'CANDIDATE_ALREADY_EXISTS')
    expected = source_tree(source)
    target.mkdir(mode=0o750)
    for directory, dirs, files in os.walk(source, followlinks=False):
        if Path(directory) == source:
            dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
            # next-env.d.ts is copied for fidelity but may be regenerated by Next.
            files = [name for name in files if name != 'tsconfig.tsbuildinfo']
        for name in dirs + files:
            need(not (Path(directory) / name).is_symlink(), 'SOURCE_LINK_REFUSED')
        relative = Path(directory).relative_to(source)
        destination = target / relative
        destination.mkdir(exist_ok=True)
        for name in files:
            original, copied = Path(directory) / name, destination / name
            raw = regular(original)
            info = original.stat()
            write_new(copied, raw, stat.S_IMODE(info.st_mode))
            shutil.copystat(original, copied, follow_symlinks=False)
            os.chown(copied, info.st_uid, info.st_gid, follow_symlinks=False)
        info = Path(directory).stat()
        shutil.copystat(directory, destination, follow_symlinks=False)
        os.chown(destination, info.st_uid, info.st_gid, follow_symlinks=False)
    need(source_tree(source) == expected == source_tree(target), 'SOURCE_CHANGED_DURING_COPY')
    return expected


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors, self.assets, self.passwords = [], set(), 0
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.link = [attrs.get('href', ''), '']
        if tag == 'input' and attrs.get('type') == 'password':
            self.passwords += 1
        if tag in ('script', 'link'):
            value = attrs.get('src' if tag == 'script' else 'href', '')
            parsed = urlsplit(value)
            if not parsed.netloc and not parsed.query and parsed.path.startswith('/_next/static/'):
                need('..' not in Path(parsed.path).parts, 'UNSAFE_HTML_ASSET_PATH')
                self.assets.add(parsed.path)

    def handle_data(self, data):
        if self.link is not None:
            self.link[1] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.link is not None:
            self.anchors.append(tuple(self.link))
            self.link = None


def assert_menu_html(html, locale, build_id, has_admin=True):
    need(build_id.encode() in html, 'FRONTEND_BUILD_ID_MISMATCH')
    page = Page()
    page.feed(html.decode('utf-8', 'strict'))
    links = [(href, label.strip()) for href, label in page.anchors if href == f'/{locale}/admin']
    need(links == [(f'/{locale}/admin', LABELS[locale])] * 2 if has_admin else not links,
         'DESKTOP_OR_MOBILE_ADMIN_LINK_MISMATCH')
    need(page.assets and any(path.endswith('.js') for path in page.assets), 'PAGE_ASSETS_MISSING')
    return page.assets


class Release:
    def __init__(self, prior):
        self.prior = prior
        self.work = None
        self.sequence = 0
        self.started = self.persisted = self.switched = self.reloaded = self.complete = False
        self.new_dump = None

    def command(self, label, argv, *, env=None, cwd=None, data=None, timeout=30, log=False):
        proc = subprocess.Popen([str(arg) for arg in argv], cwd=cwd, env=env or SYSTEM_ENV,
                                stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            output, errors = proc.communicate(input=data, timeout=timeout)
        except BaseException:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            raise Stop('COMMAND_INTERRUPTED_OR_TIMED_OUT') from None
        if log and self.work:
            self.sequence += 1
            write_new(self.work / f'{self.sequence:02d}-{label}.log', output + errors)
        need(proc.returncode == 0, 'COMMAND_FAILED_' + label.upper().replace('-', '_'))
        return output

    def journal(self, state):
        write_new(self.work / (state + '.json'), packed({
            'state': state, 'patch_sha': PATCH_SHA, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'backend_modified': False, 'credentials_changed': False, 'payment_attempted': False,
        }))

    def rows(self):
        socket, pid_file = PM2_HOME / 'rpc.sock', PM2_HOME / 'pm2.pid'
        need(socket.is_socket() and not socket.is_symlink(), 'EXISTING_PM2_SOCKET_MISSING')
        pid = int(regular(pid_file).strip())
        need(pid > 1, 'PM2_DAEMON_IDENTITY_INVALID')
        os.kill(pid, 0)
        identity = (pid, socket.stat().st_dev, socket.stat().st_ino)
        if hasattr(self, 'daemon_identity'):
            need(identity == self.daemon_identity, 'PM2_DAEMON_CHANGED')
        self.daemon_identity = identity
        return json.loads(self.command('pm2-read', ['/usr/sbin/runuser', '-u', 'act', '--', NODE,
            '-e', self.prior.PM2_READ, self.prior.PM2_ROOT, socket], env=self.prior.act_env(), timeout=25))

    def backend(self):
        current = BACK_ROOT / 'current'
        resolved = current.resolve(strict=True)
        need(current.is_symlink() and resolved.is_relative_to(BACK_ROOT / 'releases'),
             'BACKEND_POINTER_UNEXPECTED')
        raw = self.command('backend-identity', ['/usr/bin/systemctl', 'show', 'act.service', '--no-pager',
            '-p', 'ActiveState', '-p', 'MainPID', '-p', 'ExecMainStartTimestampMonotonic'])
        service = dict(line.split('=', 1) for line in raw.decode().splitlines() if '=' in line)
        pid = int(service.get('MainPID', '0'))
        need(service.get('ActiveState') == 'active' and pid > 1
             and Path(f'/proc/{pid}/cwd').resolve(strict=True) == resolved,
             'BACKEND_PROCESS_UNEXPECTED')
        return {'pointer': os.readlink(current), 'cwd': str(resolved), 'service': service,
                'env_sha256': digest(regular(BACK_ROOT / 'shared/.env')),
                'release_sha256': digest(regular(resolved / 'release.json'))}

    def public_environment(self, row, root=ACTIVE):
        overrides = extract_public_overrides(row)
        values = json.loads(self.command('public-environment', ['/usr/sbin/runuser', '-u', 'act', '--',
            NODE, '-e', self.prior.ENV_READ, root], env=self.prior.act_env() | overrides))
        return validate_public(values, compiled_keys(root))

    def other_nginx(self):
        raw = self.command('nginx-read', ['/usr/sbin/nginx', '-T'])
        parts = re.split(rb'(?m)^# configuration file (.+):\n', raw)
        seen = 0
        for index in range(1, len(parts), 2):
            if parts[index].decode() in (str(SITE), str(self.site)):
                seen += 1
                parts[index + 1] = b'ACT_SITE_CHECKED_SEPARATELY\n'
        need(seen == 1, 'ACT_SITE_INCLUDE_UNEXPECTED')
        return digest(b'\0'.join(parts))

    def unused_port(self):
        need(not self.command('candidate-port', ['/usr/bin/ss', '-H', '-ltn', f'sport = :{PORT}']).strip(),
             'CANDIDATE_PORT_IN_USE')

    def snapshot(self):
        need(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
        for path in (ACTIVE, OLD_ASSETS):
            need(path.is_dir() and path.resolve(strict=True) == path, 'ACTIVE_FRONTEND_PATH_CHANGED')
        for path in (CANDIDATE, NEW_ASSETS, RECORD):
            need(not path.exists() and not path.is_symlink(), 'PREVIOUS_ATTEMPT_EXISTS_USE_STATUS')
        self.unused_port()
        self.site = SITE.resolve(strict=True)
        need(self.site.is_relative_to(Path('/etc/nginx')), 'SITE_OUTSIDE_NGINX')
        self.original = regular(self.site)
        need(digest(self.original) == SITE_HASH, 'NGINX_DIFFERS_FROM_OWNER_SNAPSHOT')
        self.proposed, self.rollback_config = route_pair(self.original)
        self.old_build = regular(ACTIVE / '.next/BUILD_ID').decode().strip()
        need(self.old_build == OLD_BUILD, 'ACTIVE_BUILD_CHANGED')
        for locale in LABELS:
            patch_menu(regular(ACTIVE / f'src/dictionaries/{locale}/home.json'), locale)
        rows = self.rows()
        need(rows and len({row['name'] for row in rows}) == len(rows), 'PM2_NAMES_AMBIGUOUS')
        matches = [row for row in rows if row['pm2_env'].get('pm_cwd') == str(ACTIVE)]
        need(len(matches) == 1 and all(row['name'] != NAME for row in rows), 'ACTIVE_PROCESS_AMBIGUOUS')
        self.current = matches[0]
        env = self.current['pm2_env']
        need(env.get('pm_exec_path') == str(ACTIVE / 'node_modules/next/dist/bin/next')
             and env.get('exec_interpreter') == str(NODE)
             and env.get('args') == ['start', '--hostname', '127.0.0.1', '--port', '3005']
             and env.get('status') == 'online' and self.current.get('pid', 0) > 1,
             'ACTIVE_FRONTEND_LAUNCH_CHANGED')
        listeners = self.command('active-listener', ['/usr/bin/ss', '-H', '-ltnp', 'sport = :3005'])
        need(set(re.findall(rb'pid=(\d+)', listeners)) == {str(self.current['pid']).encode()}
             and Path(f'/proc/{self.current["pid"]}/cwd').resolve(strict=True) == ACTIVE,
             'ACTIVE_LISTENER_IDENTITY_CHANGED')
        self.original_dump = regular(DUMP)
        self.saved_list = json.loads(self.original_dump)
        need(isinstance(self.saved_list, list) and len(self.saved_list) == len(rows), 'SAVED_PM2_INVENTORY_DRIFT')
        for row in rows:
            saved = self.prior.one(self.saved_list, row['name'])
            need(all(saved.get(key) == row['pm2_env'].get(key) for key in self.prior.LAUNCH),
                 'SAVED_PM2_CONFIGURATION_DRIFT')
        self.ids = [self.prior.identity(row) for row in rows]
        self.public = self.public_environment(self.current)
        self.source = source_tree(ACTIVE)
        self.assets_before = self.prior.tree(OLD_ASSETS)
        self.backend_baseline = self.backend()
        self.master_hash = digest(regular(MASTER))
        self.entries = sorted(SITE.parent.iterdir())
        self.other_nginx_hash = self.other_nginx()
        self.lock_identity = (LOCK.stat().st_dev, LOCK.stat().st_ino)
        self.old_pages = self.verify_pages('http://127.0.0.1:3005', self.old_build, OLD_ASSETS,
                                            direct=True, has_admin=False)

    def guard(self, expected_route, candidate=None):
        need(SITE.resolve(strict=True) == self.site and regular(self.site) == expected_route,
             'LIVE_NGINX_PREIMAGE_DRIFT')
        need(digest(regular(MASTER)) == self.master_hash and sorted(SITE.parent.iterdir()) == self.entries
             and self.other_nginx() == self.other_nginx_hash, 'OTHER_NGINX_CONFIGURATION_DRIFT')
        need((LOCK.stat().st_dev, LOCK.stat().st_ino) == self.lock_identity, 'DEPLOYMENT_LOCK_REPLACED')
        need(self.backend() == self.backend_baseline, 'BACKEND_CHANGED_DURING_FRONTEND_RELEASE')
        need(regular(ACTIVE / '.next/BUILD_ID').decode().strip() == self.old_build
             and source_tree(ACTIVE) == self.source and self.prior.tree(OLD_ASSETS) == self.assets_before,
             'RETAINED_FRONTEND_SOURCE_OR_ASSETS_CHANGED')
        rows = self.rows()
        need(all(any(self.prior.identity(row) == old for row in rows) for old in self.ids),
             'RETAINED_PM2_PROCESS_CHANGED')
        present = [row for row in rows if row['name'] == NAME]
        need(len(rows) == len(self.ids) + len(present) and len(present) <= 1,
             'UNEXPECTED_PM2_PROCESS_CHANGE')
        need(candidate is None or len(present) == int(candidate), 'CANDIDATE_PROCESS_COUNT_MISMATCH')
        if present:
            self.verify_candidate_row(present[0], healthy=candidate is not None)
        current = self.prior.one(rows, self.current['name'])
        need(self.public_environment(current) == self.public, 'CURRENT_PUBLIC_CONFIGURATION_CHANGED')
        return rows

    def http(self, address, *, direct=False, origin=False):
        args = ['/usr/bin/curl', '--silent', '--show-error', '--noproxy', '*', '--connect-timeout', '3',
                '--max-time', '12', '--max-filesize', '16777216', '-H', 'Accept-Encoding: identity',
                '-H', 'Cache-Control: no-cache', '-w', '\n%{http_code}']
        if direct:
            args += ['-H', 'Host: ' + DOMAIN, '-H', 'X-Forwarded-Proto: https']
        if origin:
            args += ['--insecure', '--resolve', DOMAIN + ':443:127.0.0.1']
        raw = self.command('frontend-get', [*args, address], timeout=18)
        body, code = raw.rsplit(b'\n', 1)
        need(code == b'200', 'FRONTEND_HTTP_NOT_200')
        return body

    def verify_pages(self, base, build_id, assets_root, *, direct=False, origin=False,
                     has_admin=True, expected=None):
        results = {}
        nonce = str(time.time_ns())
        for locale in LABELS:
            html = self.http(f'{base}/{locale}?act_admin_header={nonce}', direct=direct, origin=origin)
            assets = assert_menu_html(html, locale, build_id, has_admin)
            if expected is not None:
                need(assets == expected[locale], 'FRONTEND_ASSET_REFERENCES_CHANGED')
            checked = set()
            for value in sorted(assets):
                extension = Path(value).suffix
                if extension not in ('.js', '.css') or extension in checked:
                    continue
                checked.add(extension)
                target = assets_root / value.removeprefix('/_next/static/')
                body = self.http(base + quote(value, safe='/._-') + '?act_admin_header=' + nonce,
                                 direct=direct, origin=origin)
                need(digest(body) == digest(regular(target)), 'SERVED_ASSET_HASH_MISMATCH')
            need(checked == {'.js', '.css'}, 'JAVASCRIPT_AND_CSS_CHECK_REQUIRED')
            form = self.http(f'{base}/{locale}/admin?act_admin_header={nonce}', direct=direct, origin=origin)
            parsed = Page()
            parsed.feed(form.decode('utf-8', 'strict'))
            need(build_id.encode() in form and parsed.passwords > 0, 'EXISTING_ADMIN_SIGNIN_NOT_RENDERED')
            results[locale] = assets
        return results

    def verify_public(self, *, rollback=False):
        for attempt in range(3):
            try:
                for origin in (True, False):
                    self.verify_pages('https://' + DOMAIN, self.old_build if rollback else self.new_build,
                        NEW_ASSETS, origin=origin, has_admin=not rollback,
                        expected=self.old_pages if rollback else self.new_pages)
                return
            except Stop:
                if attempt == 2:
                    raise
                time.sleep(2)

    def prepare(self):
        self.guard(self.original, candidate=False)
        need(regular(DUMP) == self.original_dump, 'PM2_DUMP_DRIFT')
        RECORD.mkdir(mode=0o700)
        self.work = RECORD
        self.journal('PREPARATION_STARTED')
        for name, data in [('nginx.before.conf', self.original), ('nginx.proposed.conf', self.proposed),
                           ('nginx.rollback.conf', self.rollback_config), ('pm2.before.json', self.original_dump),
                           ('public-environment.json', packed(self.public)), ('source.before.json', packed(self.source))]:
            write_new(RECORD / name, data)
        copy_source(ACTIVE, CANDIDATE)
        for locale in LABELS:
            path = CANDIDATE / f'src/dictionaries/{locale}/home.json'
            self.prior.atomic_file(path, patch_menu(regular(path), locale), MENU_BEFORE[locale])
        self.expected_source = dict(self.source)
        for locale in LABELS:
            self.expected_source[f'src/dictionaries/{locale}/home.json'] = MENU_AFTER[locale]
        need(source_tree(CANDIDATE) == self.expected_source, 'CANDIDATE_SOURCE_SCOPE_MISMATCH')
        # Preserve current app-specific PM2 settings for server-rendered build
        # code too. PM2 bookkeeping objects are not OS environment variables.
        runtime_strings = {key: value for key, value in self.current['pm2_env'].get('env', {}).items()
                           if isinstance(key, str) and isinstance(value, str)}
        env = self.prior.act_env() | runtime_strings | self.public | {
            'PATH': str(NODE_DIR) + ':/usr/bin:/bin', 'NODE_ENV': 'production',
            'NEXT_TELEMETRY_DISABLED': '1', 'npm_config_update_notifier': 'false',
        }
        emit('BUILDING_ADMIN_HEADER_CANDIDATE; CURRENT_WEBSITE_STILL_RUNNING')
        self.command('npm-ci', ['/usr/sbin/runuser', '-u', 'act', '--', NPM, 'ci', '--include=dev',
            '--ignore-scripts', '--no-audit', '--no-fund'], cwd=CANDIDATE, env=env, timeout=600, log=True)
        self.command('next-build', ['/usr/sbin/runuser', '-u', 'act', '--', NODE,
            CANDIDATE / 'node_modules/next/dist/bin/next', 'build'], cwd=CANDIDATE, env=env, timeout=600, log=True)
        need(source_tree(CANDIDATE) == self.expected_source, 'SOURCE_OR_LOCK_CHANGED_DURING_BUILD')
        validate_public(self.public, compiled_keys(CANDIDATE))
        self.new_build = regular(CANDIDATE / '.next/BUILD_ID').decode().strip()
        need(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.new_build) is not None
             and self.new_build != self.old_build, 'CANDIDATE_BUILD_ID_INVALID')
        self.assets_new = self.prior.copy_assets([OLD_ASSETS, CANDIDATE / '.next/static'], NEW_ASSETS)
        for label in ('proposed', 'rollback'):
            config = RECORD / f'nginx.{label}.conf'
            full = RECORD / f'nginx.{label}.master.conf'
            write_new(full, self.prior.validation_master(regular(MASTER), self.entries, config))
            self.command('nginx-validate-' + label, ['/usr/sbin/nginx', '-t', '-c', full, '-p', '/etc/nginx/'], log=True)
        self.guard(self.original, candidate=False)
        need(regular(DUMP) == self.original_dump, 'PM2_DUMP_DRIFT_DURING_BUILD')
        write_new(RECORD / 'plan.json', packed({
            'patch_sha': PATCH_SHA, 'source_basis': str(ACTIVE), 'source_basis_sha256': digest(packed(self.source)),
            'candidate_source_sha256': digest(packed(self.expected_source)), 'old_build_id': self.old_build,
            'new_build_id': self.new_build, 'candidate': str(CANDIDATE), 'assets': str(NEW_ASSETS),
            'name': NAME, 'port': PORT, 'original_nginx_sha256': digest(self.original),
            'proposed_nginx_sha256': digest(self.proposed), 'rollback_nginx_sha256': digest(self.rollback_config),
            'public_environment_sha256': digest(packed(self.public)), 'backend': self.backend_baseline,
            'credentials_changed': False, 'source_is_active_copy_plus_approved_patch': True,
        }))
        self.journal('CANDIDATE_BUILT_AND_CONFIGS_VALIDATED')

    def candidate_config(self):
        runtime = copy.deepcopy(self.current['pm2_env'].get('env', {}))
        # PM2 God.prepare assigns a new UUID for each process. It is daemon
        # metadata, not an application setting to inherit from the old process.
        runtime.pop('unique_id', None)
        runtime.update(self.public)
        runtime.update({'NODE_ENV': 'production', 'NEXT_TELEMETRY_DISABLED': '1',
                        'ACT_TRACKING_ACTIVATION': str(RECORD), 'ACT_ADMIN_HEADER_RELEASE': PATCH_SHA})
        if 'PORT' in runtime:
            runtime['PORT'] = str(PORT)
        return {'name': NAME, 'cwd': str(CANDIDATE), 'script': str(CANDIDATE / 'node_modules/next/dist/bin/next'),
                'interpreter': str(NODE), 'args': ['start', '--hostname', '127.0.0.1', '--port', str(PORT)],
                'exec_mode': 'fork', 'instances': 1, 'watch': False, 'env': runtime, **self.prior.POLICY}

    def verify_candidate_row(self, row, *, healthy=True):
        expected, env = self.candidate_config(), row['pm2_env']
        need((not healthy or (row.get('pid', 0) > 1 and env.get('status') == 'online'))
             and env.get('pm_cwd') == expected['cwd'] and env.get('pm_exec_path') == expected['script']
             and env.get('exec_interpreter') == expected['interpreter'] and env.get('args') == expected['args']
             and env.get('env', {}).get('ACT_TRACKING_ACTIVATION') == str(RECORD)
             and all(env.get('env', {}).get(k) == v for k, v in expected['env'].items()),
             'CANDIDATE_CONFIGURATION_MISMATCH')
        unique_id = env.get('env', {}).get('unique_id')
        need(isinstance(unique_id, str) and re.fullmatch(
            r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',
            unique_id) is not None, 'CANDIDATE_PROCESS_IDENTITY_INVALID')
        need(unique_id != self.current['pm2_env'].get('env', {}).get('unique_id'),
             'CANDIDATE_PROCESS_IDENTITY_REUSED')
        if hasattr(self, 'candidate_unique_id'):
            need(unique_id == self.candidate_unique_id, 'CANDIDATE_PROCESS_IDENTITY_CHANGED')
        self.candidate_unique_id = unique_id

    def start(self):
        self.guard(self.original, candidate=False)
        self.unused_port()
        need(regular(DUMP) == self.original_dump, 'PM2_DUMP_DRIFT_BEFORE_START')
        config = self.candidate_config()
        payload = {'socket': str(PM2_HOME / 'rpc.sock'), 'pid_file': str(PM2_HOME / 'pm2.pid'),
                   'daemon_pid': self.daemon_identity[0], 'retained': self.ids,
                   'identity_fields': list(self.prior.IDENTITY), 'config': config, 'policy': self.prior.POLICY}
        self.started = True
        self.journal('CANDIDATE_START_ATTEMPTED')
        self.command('pm2-start', ['/usr/sbin/runuser', '-u', 'act', '--', NODE, '-e',
            self.prior.PM2_START, self.prior.PM2_ROOT], env=self.prior.act_env(), data=packed(payload), timeout=40, log=True)
        rows = self.guard(self.original, candidate=True)
        need(regular(DUMP) == self.original_dump, 'PM2_DUMP_DRIFT_DURING_START')
        for attempt in range(5):
            try:
                self.new_pages = self.verify_pages(f'http://127.0.0.1:{PORT}', self.new_build,
                                                   CANDIDATE / '.next/static', direct=True)
                break
            except Stop:
                if attempt == 4:
                    raise
                time.sleep(1)
        self.journal('CANDIDATE_BILINGUAL_MENU_AND_SIGNIN_VERIFIED')
        return self.prior.one(rows, NAME)

    def persist(self, candidate):
        self.guard(self.original, candidate=True)
        need(regular(DUMP) == self.original_dump, 'PM2_DUMP_DRIFT_BEFORE_PERSIST')
        saved = copy.deepcopy(candidate['pm2_env'])
        for field in ('instances', 'pm_id', 'prev_restart_delay', '_tree_pids'):
            saved.pop(field, None)
        self.new_dump = packed([*self.saved_list, saved])
        self.persisted = True
        self.journal('PM2_DUMP_WRITE_ATTEMPTED')
        self.prior.atomic_file(DUMP, self.new_dump, digest(self.original_dump))
        self.journal('CANDIDATE_PERSISTED')

    def switch(self):
        self.guard(self.original, candidate=True)
        need(regular(DUMP) == self.new_dump and source_tree(CANDIDATE) == self.expected_source
             and self.prior.tree(NEW_ASSETS) == self.assets_new, 'PRE_SWITCH_ARTIFACT_DRIFT')
        validate_public(self.public, compiled_keys(CANDIDATE))
        self.switched = True
        self.journal('NGINX_SWITCH_ATTEMPTED')
        self.prior.atomic_file(self.site, self.proposed, digest(self.original))
        self.command('nginx-test-live', ['/usr/sbin/nginx', '-t'], log=True)
        self.reloaded = True
        self.journal('NGINX_RELOAD_ATTEMPTED')
        self.command('nginx-reload', ['/usr/bin/systemctl', 'reload', 'nginx.service'], log=True)
        self.guard(self.proposed, candidate=True)
        self.verify_public()
        self.guard(self.proposed, candidate=True)
        need(regular(DUMP) == self.new_dump, 'PM2_DUMP_DRIFT_AFTER_SWITCH')
        self.journal('ADMIN_HEADER_DEPLOYED')
        self.complete = True
        emit('ADMIN_HEADER_DEPLOYED; ENGLISH_AND_ARABIC_VERIFIED; STRIPE_TEST_CONFIGURATION_PRESERVED')
        emit('BACKEND_UNCHANGED; PREVIOUS_FRONTEND_RETAINED')

    def rollback(self):
        if not self.work or not self.started or self.complete:
            return
        current = regular(self.site)
        need(current in (self.original, self.proposed, self.rollback_config), 'ROLLBACK_NGINX_UNKNOWN')
        self.guard(current, candidate=None)
        current_dump = regular(DUMP)
        need(current_dump == self.original_dump or (self.new_dump is not None and current_dump == self.new_dump),
             'ROLLBACK_PM2_DUMP_UNKNOWN')
        self.journal('ROLLBACK_STARTED')
        target = self.rollback_config if current != self.original or self.reloaded else self.original
        if current != target:
            self.prior.atomic_file(self.site, target, digest(current))
        self.command('rollback-nginx-test', ['/usr/sbin/nginx', '-t'], log=True)
        if self.reloaded:
            self.command('rollback-nginx-reload', ['/usr/bin/systemctl', 'reload', 'nginx.service'], log=True)
        if current_dump != self.original_dump:
            self.prior.atomic_file(DUMP, self.original_dump, digest(current_dump))
        # Revalidate daemon/socket, retained rows and candidate ownership directly
        # before the existing guarded removal primitive. A failed candidate need
        # not be healthy in order to return traffic to the retained old frontend.
        self.guard(target, candidate=None)
        config = self.candidate_config()
        payload = {'socket': str(PM2_HOME / 'rpc.sock'), 'retained': self.ids,
                   'identity_fields': list(self.prior.IDENTITY), 'name': NAME,
                   'cwd': config['cwd'], 'script': config['script'], 'interpreter': config['interpreter'],
                   'args': config['args'], 'activation_nonce': str(RECORD), 'allow_absent': True}
        self.command('candidate-remove', ['/usr/sbin/runuser', '-u', 'act', '--', NODE, '-e',
            self.prior.PM2_REMOVE, self.prior.PM2_ROOT], env=self.prior.act_env(), data=packed(payload), timeout=35, log=True)
        self.guard(target, candidate=False)
        need(regular(DUMP) == self.original_dump, 'ROLLBACK_PM2_NOT_RESTORED')
        if self.reloaded:
            self.verify_public(rollback=True)
        self.journal('PREVIOUS_FRONTEND_RESTORED')
        emit('PREVIOUS_FRONTEND_RESTORED; BACKEND_UNCHANGED; PRESERVE_RELEASE_RECORD')

    def deploy(self):
        self.prepare()
        candidate = self.start()
        self.persist(candidate)
        self.switch()


STAGES = ('PREPARATION_STARTED', 'CANDIDATE_BUILT_AND_CONFIGS_VALIDATED', 'CANDIDATE_START_ATTEMPTED',
          'CANDIDATE_BILINGUAL_MENU_AND_SIGNIN_VERIFIED', 'PM2_DUMP_WRITE_ATTEMPTED', 'CANDIDATE_PERSISTED',
          'NGINX_SWITCH_ATTEMPTED', 'NGINX_RELOAD_ATTEMPTED', 'ADMIN_HEADER_DEPLOYED',
          'ROLLBACK_STARTED', 'PREVIOUS_FRONTEND_RESTORED')


def status():
    if not RECORD.exists() and not RECORD.is_symlink():
        emit('NO_RECORDED_ADMIN_HEADER_RELEASE_ATTEMPT')
        return
    need(RECORD.is_dir() and RECORD.resolve(strict=True) == RECORD
         and RECORD.stat().st_uid == 0 and not RECORD.stat().st_mode & 0o077, 'PRIVATE_RELEASE_RECORD_INVALID')
    found = []
    for stage in STAGES:
        marker = RECORD / (stage + '.json')
        if marker.exists():
            value = json.loads(regular(marker))
            need(value.get('state') == stage and value.get('patch_sha') == PATCH_SHA, 'RELEASE_JOURNAL_MISMATCH')
            found.append(stage)
    emit('RECORDED_ADMIN_HEADER_STATUS: ' + (found[-1] if found else 'RECORD_CREATED'))
    emit('READ_ONLY_JOURNAL_REPORT; DO_NOT_REPEAT_DEPLOY')


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop('EXPECTED_ONLY_CHECK_DEPLOY_OR_STATUS')


def main(argv=None):
    try:
        parser = SafeParser(description=__doc__)
        mode = parser.add_mutually_exclusive_group(required=True)
        for value in ('check', 'deploy', 'status'):
            mode.add_argument('--' + value, action='store_true')
        args = parser.parse_args(argv)
        need(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
        os.umask(0o077)
        if args.status:
            status()
            return 0
        prior = load_prior()
        need(LOCK.is_file() and not LOCK.is_symlink(), 'DEPLOYMENT_LOCK_MISSING')
        with LOCK.open('rb') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Stop('ANOTHER_DEPLOYMENT_IS_IN_PROGRESS') from None
            release = Release(prior)
            release.snapshot()
            if args.check:
                emit('ADMIN_HEADER_PREFLIGHT_PASSED; READ_ONLY; NO_CHANGES')
                return 0
            # Approval was supplied in the ACT development chat for this exact patch.
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            def interrupted(_number, _frame):
                raise Stop('OPERATOR_INTERRUPTED_RELEASE')
            signal.signal(signal.SIGINT, interrupted)
            signal.signal(signal.SIGTERM, interrupted)
            try:
                release.deploy()
            except (Exception, KeyboardInterrupt) as exc:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                code = str(exc) if isinstance(exc, Stop) else 'RELEASE_OPERATION_FAILED'
                try:
                    release.rollback()
                except (Exception, KeyboardInterrupt):
                    emit('STOPPED: RECOVERY_INCOMPLETE; PRESERVE_PRIVATE_RECORD; DO_NOT_REPEAT_DEPLOY')
                    return 2
                emit('STOPPED: ' + code + '; PRESERVED_OR_ROLLED_BACK; DO_NOT_REPEAT_DEPLOY')
                return 1
        return 0
    except Stop as exc:
        emit('STOPPED: ' + str(exc) + '; NO_NEW_ACTIVATION')
        return 1
    except (Exception, KeyboardInterrupt):
        emit('STOPPED: PREFLIGHT_UNAVAILABLE; NO_NEW_ACTIVATION; NO_SECRET_DETAILS_PRINTED')
        return 1


if __name__ == '__main__':
    sys.exit(main())
