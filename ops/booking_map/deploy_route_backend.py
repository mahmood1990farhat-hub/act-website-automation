#!/usr/bin/env python3
"""Deploy only the owner-approved route-preview backend without new database migration.

Run with Python 3.11+ as root and --deploy. All identities and destinations are
pinned. Repeating the command reconciles the same private receipt; it never
rebuilds a verified stage, repeats an applied migration, or prunes a release.
This helper deliberately does not operate the frontend, workers or live trips.
"""

import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
import traceback
from urllib.parse import urlsplit


APP_SHA = 'c1638d38898eff1363c8bdf07783dbbe9264a220'
BASE_SHA = '370dc89af105788ef598d0475c1ace20fd05826f'
APP_TREE = 'a391f04a7eca2a3b00a99e6a32ed8fc315bb0791'
BACKEND_TREE = '365ecd6f1faf2e6cfc4db258390a0741fba7fde7'
SUBTREE = 'act_backend-main'
REPO = Path('/var/www/atg/front-end/airportandcitytransfer_repo')
ROOT = Path('/var/www/atg/atg-backend')
CURRENT = ROOT / 'current'
BASE = ROOT / 'releases/20261123-report-370dc89/backend'
VENV = ROOT / 'releases/20261015T-ready-735c966/backend/.venv'
RELEASE = ROOT / 'releases/20261125-route-c1638d3/backend'
RECORD = Path('/root/act-release-backup/booking-route-c1638d3')
LOCK = Path('/run/lock/act-backend-deploy.lock')
MIGRATION = '0009_journey_timestamps'
TRIPS_BASE = ['0001_initial', '0002_alter_trip_status',
              '0003_trip_booking_confirmation_pdf_and_more',
              '0004_booking_details_persistence', '0005_booking_confirmation_delivery_state',
              '0006_driver_details_reminder', '0007_external_driver_passenger_identity',
              '0008_refund_outcome_tracking']
SHARED = ('.env', 'media', 'static', 'logs')
CHANGED = {
    'apps/trips/services/route_preview.py',
    'apps/trips/tests/test_route_preview.py',
    'apps/trips/urls.py',
    'apps/trips/views/calculate_trip_cost.py',
    'apps/trips/views/route_preview.py',
    'myProject/settings/base.py',
}
SYSTEM_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8',
              'PYTHONDONTWRITEBYTECODE': '1'}
API_PATH = '/api/driver/trips/37/'


# Invoked only with the retained interpreter. Its output stays in private logs;
# the parent emits only selected boolean/count results. No credential is printed.
DATABASE_TASK = r'''
import json, os, subprocess, sys
from pathlib import Path
import environ
mode, release, argument = sys.argv[1:]
release = Path(release)
e = environ.Env(); environ.Env.read_env(release / '.env')
target = ('trips', '0009_journey_timestamps')
result = {}
if mode == 'resources':
    firebase = e('FIREBASE_CREDENTIALS_PATH', default='airport-city-transfer-33ac7-firebase-adminsdk-fbsvc-aba3144ea6.json')
    result = {'firebase': firebase}
elif mode in ('inspect', 'backup'):
    import psycopg2
    options = dict(dbname=e('DB_NAME'), user=e('DB_USER'), password=e('DB_PASSWORD'),
                   host=e('DB_HOST', default='localhost'), port=e('DB_PORT', default='5432'),
                   options='-c default_transaction_read_only=on -c statement_timeout=15000', connect_timeout=10)
    if mode == 'backup':
        child = os.environ.copy(); child['PGPASSWORD'] = options['password']
        child['PGOPTIONS'] = '-c default_transaction_read_only=on'
        subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--no-privileges',
                        '--host', options['host'], '--port', str(options['port']),
                        '--username', options['user'], '--file', argument, options['dbname']],
                       check=True, env=child)
        subprocess.run(['pg_restore', '--list', argument], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['pg_restore', '--file', os.devnull, argument], check=True, stdout=subprocess.DEVNULL)
        result = {'backup_verified': True}
    else:
        with psycopg2.connect(**options) as connection, connection.cursor() as cursor:
            cursor.execute('SHOW transaction_read_only'); assert cursor.fetchone()[0] == 'on'
            cursor.execute('SELECT name FROM django_migrations WHERE app=%s ORDER BY name', ('trips',))
            result['migrations'] = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT column_name, is_nullable, data_type, column_default FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='trips_trip' AND column_name IN ('started_at', 'completed_at') ORDER BY column_name")
            result['columns'] = [list(row) for row in cursor.fetchall()]
            fields = 'started_at, completed_at' if len(result['columns']) == 2 else 'NULL, NULL'
            cursor.execute('SELECT status, is_paid, base_driver_id, '+fields+' FROM trips_trip WHERE id=37')
            row = cursor.fetchone(); assert row is not None
            result['trip37'] = {'status': row[0], 'paid': row[1], 'driver_id': row[2],
                                'started_null': row[3] is None, 'completed_null': row[4] is None}
            for label, table in [('driver', 'earnings_driverearningledger'), ('company', 'earnings_companyrevenueledger')]:
                cursor.execute('SELECT COUNT(*) FROM '+table+' WHERE trip_id=37')
                result['trip37'][label+'_count'] = cursor.fetchone()[0]
            result['read_only'] = True
else:
    os.chdir(release); sys.path.insert(0, str(release))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'myProject.settings'
    import django
    django.setup()
    from django.db import connection, transaction
    from django.db.migrations.executor import MigrationExecutor
    if mode in ('plan', 'migrate'):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '60s'")
            executor = MigrationExecutor(connection)
            executor.loader.check_consistent_history(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            result['plan'] = [[migration.app_label, migration.name, backwards] for migration, backwards in plan]
            assert result['plan'] in ([], [['trips', target[1], False]])
            if mode == 'migrate':
                assert result['plan'] == [['trips', target[1], False]]
                migration = executor.loader.get_migration(*target)
                assert migration.atomic and [(type(op).__name__, op.name) for op in migration.operations] == [('AddField', 'started_at'), ('AddField', 'completed_at')]
                # Execute only the approved target inside one transaction. No
                # unrelated post_migrate handlers or application actions run.
                executor.migrate([target])
                refreshed = MigrationExecutor(connection)
                assert not refreshed.migration_plan(refreshed.loader.graph.leaf_nodes())
                result['applied'] = True
    elif mode == 'report':
        from types import SimpleNamespace
        from apps.trips.models import Trip
        from apps.trips.serializers.trip import DriverTripDetailSerializer
        trip = Trip.objects.select_related('base_driver__user', 'driver_earning', 'car_type').get(pk=37)
        serializer = DriverTripDetailSerializer(context={'request': SimpleNamespace(user=trip.base_driver.user)})
        report = serializer.get_journey_report(trip)
        assert report and report['schema_version'] == 1 and report['trip_id'] == 37 and report['status'] == 'completed'
        assert report['timing_status'] == 'not_recorded' and report['started_at'] is None and report['completed_at'] is None and report['actual_duration_seconds'] is None
        result = {'report_schema': 1, 'legacy_times_not_recorded': True}
    else:
        raise ValueError('Unknown database task')
print('ACT_ROLLOUT_JSON='+json.dumps(result, sort_keys=True))
'''


class Stop(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


def say(message):
    try:
        print(message, flush=True)
    except BrokenPipeError:
        pass  # A disconnected terminal must not interrupt the private journal.


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_hash(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def private_json(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    descriptor, temporary = tempfile.mkstemp(prefix='.receipt-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        Path(temporary).unlink(missing_ok=True)


def validate_schema_snapshot(snapshot):
    require(snapshot.get('read_only') is True, 'Database inspection did not confirm read-only mode.')
    migrations = snapshot.get('migrations')
    require(migrations in (TRIPS_BASE, TRIPS_BASE+[MIGRATION]), 'Applied trips migrations differ from the approved base/target.')
    applied = MIGRATION in migrations
    columns = [['completed_at', 'YES', 'timestamp with time zone', None],
               ['started_at', 'YES', 'timestamp with time zone', None]]
    require(snapshot.get('columns') == (columns if applied else []), 'Timestamp schema and migration recorder disagree.')
    trip = snapshot.get('trip37', {})
    require(trip.get('status') == 'completed' and trip.get('paid') is True and trip.get('driver_id')
            and trip.get('driver_count') == trip.get('company_count') == 1
            and trip.get('started_null') is True and trip.get('completed_null') is True,
            'Trip37 legacy status, timestamps, driver or ledger counts differ; no trip will be changed.')
    return applied


def validate_plan(plan, applied):
    require(plan == ([] if applied else [['trips', MIGRATION, False]]),
            'Pending migration plan is not exactly the approved trips0009 transition.')


def validate_manifest(root, manifest, *, linked=False, extras=()):
    expected = set()
    for relative, digest in manifest.items():
        path = PurePosixPath(relative)
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe source manifest path.')
        relative = 'static.staged/'+relative[7:] if linked and relative.startswith('static/') else relative
        expected.add(relative)
        target = root/relative
        require(target.is_file() and not target.is_symlink() and blob_hash(target.read_bytes()) == digest,
                'A pinned source file is missing or changed; no source will be overwritten.')
    observed = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        here = Path(directory)
        dirs[:] = [name for name in dirs if name != '__pycache__' and not (linked and here == root and name in (*SHARED, '.venv'))]
        for name in dirs:
            require(not (here/name).is_symlink(), 'Unexpected source directory link.')
        for name in files:
            relative = (here/name).relative_to(root).as_posix()
            if linked and relative in (*SHARED, '.venv', *extras):
                continue
            require(not (here/name).is_symlink(), 'Unexpected source file link.')
            observed.add(relative)
    require(observed == expected, 'Unexpected files in the release source; existing work is preserved.')


class Rollout:
    def __init__(self, record=RECORD):
        self.record = Path(record)
        self.state = {}
        self.activation_started = False
        self.completed = False
        self.accepted_retry = False

    def save(self, phase):
        if self.accepted_retry:
            return  # A verification-only retry never rewrites acceptance evidence.
        self.state['phase'] = phase
        self.state['updated_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        private_json(self.record/'receipt.json', self.state)

    def log_bytes(self, label, data):
        # Diagnostics are auxiliary: full/read-only storage must never prevent
        # restoring an application pointer already changed by this invocation.
        try:
            path = self.record/(str(time.time_ns())+'-'+label+'.log')
            path.write_bytes(data); path.chmod(0o600)
        except OSError:
            pass

    def log_failure(self, label):
        try:
            self.log_bytes(label, traceback.format_exc().encode('utf-8', 'backslashreplace'))
        except Exception:
            pass  # Emergency diagnostics must always leave recovery reachable.

    def run(self, label, arguments, *, cwd=None, timeout=45, env=None):
        with subprocess.Popen([str(x) for x in arguments], cwd=cwd,
                              env=SYSTEM_ENV if env is None else env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True) as process:
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except BaseException:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
                self.log_bytes(label, stdout+stderr)
                raise
        self.log_bytes(label, stdout+stderr)
        require(process.returncode == 0, label+' failed; details are in the private record.')
        return stdout

    def git(self, *arguments):
        environment = os.environ.copy(); environment['GIT_TERMINAL_PROMPT'] = '0'
        return self.run('git', ['git', '-C', REPO, *arguments], timeout=120, env=environment)

    def db_task(self, mode, *, release=RELEASE, argument=''):
        environment = dict(SYSTEM_ENV)
        environment['PGOPTIONS'] = '-c default_transaction_read_only='+('off' if mode == 'migrate' else 'on')
        raw = self.run('database-'+mode, [VENV/'bin/python', '-B', '-c', DATABASE_TASK, mode, release, argument],
                       cwd=release, env=environment, timeout=600 if mode == 'backup' else 100)
        rows = [line.removeprefix(b'ACT_ROLLOUT_JSON=') for line in raw.splitlines() if line.startswith(b'ACT_ROLLOUT_JSON=')]
        require(len(rows) == 1, 'Database task did not return exactly one receipt.')
        return json.loads(rows[0])

    def current_target(self):
        require(CURRENT.is_symlink(), 'Current backend pointer is not a symlink.')
        return CURRENT.resolve(strict=True)

    def service(self):
        properties = ('ActiveState', 'SubState', 'MainPID', 'WorkingDirectory', 'User', 'Group')
        raw = self.run('service-state', ['systemctl', 'show', 'act.service', '--no-pager', *['-p'+p for p in properties]])
        result = dict(line.split('=', 1) for line in raw.decode().splitlines() if '=' in line)
        require(result.get('WorkingDirectory') == str(CURRENT), 'act.service working-directory configuration changed.')
        pid = int(result.get('MainPID', '0'))
        result['cwd'] = str(Path('/proc', str(pid), 'cwd').resolve(strict=True)) if pid > 1 else None
        return result

    @staticmethod
    def running(service, target):
        return (service.get('ActiveState') == 'active' and service.get('SubState') == 'running'
                and service.get('cwd') == str(target))

    def http(self, public=False):
        args = ['curl', '--silent', '--show-error', '--noproxy', '*', '--connect-timeout', '3',
                '--max-time', '8', '--max-filesize', '1048576', '-H', 'Accept: application/json',
                '-H', 'Cache-Control: no-cache', '-H', 'X-Forwarded-Proto: https', '-w', '\n%{http_code}']
        args += ['https://airportandcitytransfer.com'+API_PATH] if public else [
            '--unix-socket', '/run/act.sock', '-H', 'Host: airportandcitytransfer.com', 'http://localhost'+API_PATH]
        raw = self.run('protected-http', args, timeout=12)
        body, code = raw.rsplit(b'\n', 1)
        require(int(code) in (401, 403) and isinstance(json.loads(body), dict), 'Protected API did not return a JSON authentication refusal.')
        return int(code)

    def manifest(self, sha):
        result = {}
        for row in self.git('ls-tree', '-rz', sha+':'+SUBTREE).split(b'\0'):
            if not row:
                continue
            metadata, name = row.split(b'\t', 1); mode, kind, digest = metadata.decode().split()
            require(mode == '100644' and kind == 'blob', 'Source contains an unexpected link, executable or special entry.')
            result[name.decode()] = digest
        require(result, 'Backend source manifest is empty.')
        return result

    def resource_snapshot(self):
        require((BASE/'.venv').resolve(strict=True) == VENV and (VENV/'bin/python').is_file(), 'Retained virtual environment changed.')
        require((BASE/'requirements.txt').read_bytes() == (VENV.parent/'requirements.txt').read_bytes(), 'Retained environment requirements differ.')
        for name in SHARED:
            require((BASE/name).exists() and (BASE/name).resolve(strict=True) == (ROOT/'shared'/name).resolve(strict=True), 'A shared resource link changed.')
        configured = self.db_task('resources', release=BASE)
        relative = Path(configured['firebase'])
        require(not relative.is_absolute() and '..' not in relative.parts and relative.parts,
                'Firebase arrangement differs from the inspected relative-file arrangement.')
        firebase = BASE/relative
        require(firebase.is_file() and not firebase.is_symlink(), 'Existing Firebase file is missing or linked unexpectedly.')
        info = firebase.stat()
        return {'environment_sha256': sha256((ROOT/'shared/.env').read_bytes()),
                'firebase_relative': relative.as_posix(), 'firebase_sha256': sha256(firebase.read_bytes()),
                'firebase_uid': info.st_uid, 'firebase_gid': info.st_gid, 'firebase_mode': stat.S_IMODE(info.st_mode),
                'requirements_sha256': sha256((BASE/'requirements.txt').read_bytes())}

    def verify_sources(self, target):
        manifest = self.base_manifest if target == BASE else self.app_manifest
        validate_manifest(target, manifest, linked=True, extras=('release.json', self.state['resources']['firebase_relative']))
        metadata = json.loads((target/'release.json').read_bytes())
        require(metadata.get('git_sha') == (BASE_SHA if target == BASE else APP_SHA), 'Release source metadata changed.')
        if target != BASE:
            require(metadata.get('rollout_record') == str(self.record)
                    and metadata.get('staging_nonce') == self.state.get('staging_nonce')
                    and metadata.get('venv_provider') == str(VENV), 'Candidate ownership or environment metadata changed.')
        for name in SHARED:
            require((target/name).is_symlink() and (target/name).resolve(strict=True) == (ROOT/'shared'/name).resolve(strict=True), 'Shared resource drift.')
        require((target/'.venv').is_symlink() and (target/'.venv').resolve(strict=True) == VENV, 'Retained environment link drift.')
        resources = self.state['resources']; firebase = target/resources['firebase_relative']; info = firebase.stat()
        require(not firebase.is_symlink() and sha256(firebase.read_bytes()) == resources['firebase_sha256']
                and (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) ==
                (resources['firebase_uid'], resources['firebase_gid'], resources['firebase_mode']), 'Firebase file arrangement drift.')

    def preflight(self):
        require(os.geteuid() == 0, 'Run in the approved root Hostinger session.')
        require(self.record.parent.is_dir() and not self.record.is_symlink(), 'Private recovery parent is missing or record is linked.')
        self.record.mkdir(mode=0o700, exist_ok=True)
        info = self.record.stat()
        require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700 and self.record.resolve() == self.record, 'Recovery record is not a root-private directory.')
        receipt = self.record/'receipt.json'
        identity = {'format': 1, 'app_sha': APP_SHA, 'base_sha': BASE_SHA, 'release': str(RELEASE),
                    'previous': str(BASE), 'helper_sha256': sha256(Path(__file__).read_bytes())}
        if receipt.exists():
            require(receipt.is_file() and not receipt.is_symlink(), 'Invalid existing receipt.')
            saved = json.loads(receipt.read_bytes())
            require(all(saved.get(k) == v for k, v in identity.items()), 'Existing receipt identity differs; preserved for review.')
            self.state = saved
            self.accepted_retry = saved.get('complete') is True
        else:
            require(not RELEASE.parent.exists(), 'An unrecorded candidate release already exists; preserved.')
            self.state = identity; self.save('STARTED')
        say('PRIVATE_ROLLOUT_RECORD='+str(self.record))
        require(REPO.is_dir(), 'Existing source cache is missing; no replacement clone is created.')
        remote = self.git('remote', 'get-url', 'origin').decode().strip()
        parsed = urlsplit(remote) if not remote.startswith('git@github.com:') else None
        path = remote[len('git@github.com:'):] if parsed is None else parsed.path.lstrip('/')
        require((parsed is None or parsed.hostname == 'github.com' and parsed.scheme in ('https', 'ssh'))
                and path.removesuffix('.git') == 'mahmood1990farhat-hub/act-website-automation', 'Existing source remote differs.')
        self.git('fetch', '--no-tags', '--no-write-fetch-head', 'origin', BASE_SHA, APP_SHA)
        require(self.git('rev-parse', APP_SHA+'^{tree}').decode().strip() == APP_TREE
                and self.git('rev-parse', APP_SHA+':'+SUBTREE).decode().strip() == BACKEND_TREE, 'Approved source tree differs.')

        # The reviewed combined commit is stacked on the frontend branch, not on the deployed backend.
        # Only the exact deployed and reviewed backend subtrees are compared and accepted.
        changed = {p.removeprefix(SUBTREE+'/') for p in self.git('diff', '--name-only', BASE_SHA, APP_SHA, '--', SUBTREE).decode().splitlines()}
        require(changed == CHANGED, 'Approved backend difference exceeds the report scope.')
        self.base_manifest = self.manifest(BASE_SHA); self.app_manifest = self.manifest(APP_SHA)
        resources = self.resource_snapshot()
        if 'resources' in self.state:
            require(resources == self.state['resources'], 'Shared configuration or retained resource drift; stopped.')
        else:
            self.state['resources'] = resources; self.save('RESOURCES_RECORDED')
        self.verify_sources(BASE)
        require(json.loads((BASE/'release.json').read_bytes()).get('git_sha') == BASE_SHA, 'Previous release metadata differs.')
        target = self.current_target()
        require(target in (BASE, RELEASE), 'Current source differs from both approved release identities.')
        require(not self.accepted_retry or target == RELEASE, 'Accepted release pointer changed; verification-only retry will not change it.')
        if target == RELEASE:
            require(self.state.get('staged') and self.state.get('activation_started'), 'Current candidate has no matching activation receipt.')
            self.verify_sources(RELEASE)
        self.before_service = self.service()
        owned_interruption = self.state.get('activation_started') and not self.accepted_retry
        require(self.running(self.before_service, target) or owned_interruption
                and self.before_service['cwd'] in (None, str(BASE), str(RELEASE)),
                'Running process and source pointer differ without an owned interrupted activation.')
        self.needs_restart = not self.running(self.before_service, target)
        if owned_interruption and (target == RELEASE or self.needs_restart):
            # From here a failure must recover our already-promoted/interrupted
            # application, even if access/schema/backup verification later fails.
            self.activation_started = True
        if not self.needs_restart:
            codes = [self.http(), self.http(public=True)]
            require('http_codes' not in self.state or self.state['http_codes'] == codes, 'Protected API changed before activation.')
            self.state.setdefault('http_codes', codes)
        require('http_codes' in self.state, 'No saved protected-API baseline for interrupted activation.')
        self.save('PREFLIGHT_VERIFIED')

    def stage(self):
        if self.state.get('staged'):
            self.verify_sources(RELEASE)
            return
        require(self.current_target() == BASE, 'An active candidate cannot be restaged.')
        if RELEASE.parent.exists():
            metadata = json.loads((RELEASE/'release.json').read_bytes())
            require(self.state.get('staging_started') and metadata.get('rollout_record') == str(self.record)
                    and metadata.get('staging_nonce') == self.state.get('staging_nonce')
                    and metadata.get('git_sha') == APP_SHA, 'Unowned candidate exists; it will not be overwritten.')
            self.verify_sources(RELEASE)
            self.state['staged'] = True; self.save('STAGED_NOT_ACTIVE')
            return
        archive = self.git('archive', '--format=tar', APP_SHA, SUBTREE)
        self.state['staging_started'] = True
        self.state['staging_nonce'] = os.urandom(12).hex()
        self.save('STAGING_STARTED')
        temporary = Path(tempfile.mkdtemp(prefix='20261125-route-c1638d3-stage-', dir=RELEASE.parent.parent))
        self.state.setdefault('staging_attempts', []).append(str(temporary)); self.save('STAGING_DIRECTORY_RECORDED')
        staged = temporary/'backend'; staged.mkdir(mode=0o750)
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as source:
            for member in source.getmembers():
                parts = PurePosixPath(member.name).parts
                require(parts and parts[0] == SUBTREE and '..' not in parts and not member.name.startswith('/')
                        and (member.isdir() or member.isfile()), 'Unsafe source archive member.')
                if len(parts) == 1:
                    continue
                path = staged.joinpath(*parts[1:])
                if member.isdir():
                    path.mkdir(mode=0o750, parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
                    stream = source.extractfile(member); require(stream is not None, 'Archive file cannot be read.')
                    with path.open('xb') as output:
                        shutil.copyfileobj(stream, output)
                    path.chmod(0o640)
        validate_manifest(staged, self.app_manifest)
        (staged/'static').rename(staged/'static.staged')
        for name in SHARED:
            require(not (staged/name).exists(), 'Git archive unexpectedly contains a runtime resource.')
            (staged/name).symlink_to((ROOT/'shared'/name).resolve(strict=True))
        (staged/'.venv').symlink_to(VENV)
        resources = self.state['resources']; firebase = staged/resources['firebase_relative']
        require(not firebase.exists() and not firebase.is_symlink(), 'Credential destination unexpectedly exists in source.')
        firebase.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        shutil.copy2(BASE/resources['firebase_relative'], firebase)
        group = pwd.getpwnam('www-data').pw_gid
        for directory, dirs, files in os.walk(staged, followlinks=False):
            os.chown(directory, 0, group); os.chmod(directory, 0o750)
            for name in dirs+files:
                os.chown(Path(directory)/name, 0, group, follow_symlinks=False)
        os.chown(temporary, 0, group); os.chmod(temporary, 0o750)
        os.chown(firebase, resources['firebase_uid'], resources['firebase_gid'])
        os.chmod(firebase, resources['firebase_mode'])
        private_json(staged/'release.json', {'git_sha': APP_SHA, 'state': 'STAGED_NOT_ACTIVE',
                     'requirements_sha256': resources['requirements_sha256'], 'venv_provider': str(VENV),
                     'rollout_record': str(self.record), 'staging_nonce': self.state['staging_nonce']})
        private_json(self.record/'source-manifest.json', self.app_manifest)
        self.verify_sources(staged)
        require(not RELEASE.parent.exists(), 'Candidate destination appeared concurrently; preserved.')
        os.rename(temporary, RELEASE.parent)
        self.verify_sources(RELEASE)
        self.state['staged'] = True; self.save('STAGED_NOT_ACTIVE')
        say('EXACT_BACKEND_STAGED_RESOURCES_PRESERVED')

    def guard(self):
        require(self.current_target() == BASE, 'Current backend changed before the approved transition.')
        service = self.service()
        require(service == self.before_service and self.running(service, BASE), 'Backend service changed during preparation.')
        require(self.resource_snapshot() == self.state['resources'], 'Shared configuration or retained resource changed.')
        self.verify_sources(BASE); self.verify_sources(RELEASE)

    def check_access(self):
        user = self.before_service.get('User') or 'root'
        group = self.before_service.get('Group')
        paths = ['static.staged/'+name[7:] if name.startswith('static/') else name for name in self.app_manifest]
        paths += ['.env', self.state['resources']['firebase_relative']]
        program = ('import json,sys; from pathlib import Path; root=Path(sys.argv[1]); '
                   'files=json.loads(sys.argv[2]); '
                   '[(root/name).open("rb").close() for name in files]')
        args = ['runuser', '-u', user] + (['-g', group] if group else [])
        self.run('service-user-read-access', args+['--', VENV/'bin/python', '-B', '-c', program,
                                                  RELEASE, json.dumps(paths)], cwd=RELEASE)

    def check_plan(self):
        snapshot = self.db_task('inspect')
        self.applied = validate_schema_snapshot(snapshot)
        if 'before_trip37' in self.state:
            require(snapshot['trip37'] == self.state['before_trip37'], 'Trip37 changed since the saved preimage.')
        else:
            require(self.applied, 'Existing migration 0009 is absent; no writes are permitted.')
            self.state['before_trip37'] = snapshot['trip37']
        validate_plan(self.db_task('plan')['plan'], self.applied)
        self.save('MIGRATION_STATE_VERIFIED')

    def atomic_current(self, target, expected):
        require(self.current_target() == expected, 'Concurrent backend pointer change; overwrite refused.')
        info = CURRENT.lstat(); old_link = os.readlink(CURRENT)
        temporary = CURRENT.parent/('.current-report-'+os.urandom(8).hex())
        try:
            temporary.symlink_to(target); os.chown(temporary, info.st_uid, info.st_gid, follow_symlinks=False)
            now = CURRENT.lstat()
            require(CURRENT.is_symlink() and os.readlink(CURRENT) == old_link
                    and (now.st_dev, now.st_ino) == (info.st_dev, info.st_ino), 'Concurrent backend pointer replacement; refused.')
            os.replace(temporary, CURRENT)
            descriptor = os.open(CURRENT.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            temporary.unlink(missing_ok=True)

    def restart(self):
        self.run('restart-act-only', ['systemctl', 'restart', 'act.service'], timeout=45)

    def activate(self):
        self.guard()
        self.state['activation_started'] = True; self.save('ACTIVATION_STARTED')
        self.activation_started = True
        self.atomic_current(RELEASE, BASE)
        self.restart()

    def verify(self, target=RELEASE):
        for attempt in range(5):
            try:
                require(self.current_target() == target and self.running(self.service(), target), 'Running backend source differs.')
                require([self.http(), self.http(public=True)] == self.state['http_codes'], 'Protected API readiness differs.')
                break
            except (Stop, OSError, ValueError, subprocess.TimeoutExpired):
                if attempt == 4:
                    raise Stop('Bounded backend readiness failed.')
                time.sleep(2)
        self.verify_sources(target)
        require(self.resource_snapshot() == self.state['resources'], 'Final shared resource drift.')
        snapshot = self.db_task('inspect', release=target)
        require(validate_schema_snapshot(snapshot) and snapshot['trip37'] == self.state['before_trip37'], 'Final migration or Trip37 verification failed.')
        if target == RELEASE:
            validate_plan(self.db_task('plan')['plan'], True)
            require(self.db_task('report') == {'report_schema': 1, 'legacy_times_not_recorded': True}, 'Read-only report verification failed.')

    def recover(self):
        if self.completed or self.accepted_retry:
            return
        if not self.activation_started:
            self.save('STOPPED_BEFORE_ACTIVATION')
            say('STOPPED_BEFORE_ACTIVATION_SCHEMA_MUST_BE_INSPECTED_ON_RETRY')
            return
        target = self.current_target()
        require(target in (BASE, RELEASE), 'Concurrent backend change; automatic recovery withheld.')
        require(self.resource_snapshot() == self.state['resources'], 'Resource drift; automatic recovery withheld.')
        self.verify_sources(BASE)
        if target == RELEASE:
            self.atomic_current(BASE, RELEASE)
        self.restart()
        self.verify(BASE)
        self.save('PREVIOUS_BACKEND_RESTORED_COLUMNS_RETAINED')
        say('PREVIOUS_BACKEND_RESTORED_NULLABLE_COLUMNS_RETAINED')

    def execute(self):
        try:
            self.preflight()
            self.stage()
            self.check_access()
            self.check_plan()
            # The deployed completed-journey schema is read-only in this feature release.
            # No migration, production backup restore or data changes are attempted.
            if self.current_target() == RELEASE:
                require(self.applied and self.state.get('activation_started'), 'Incomplete activation identity; stopped.')
                self.activation_started = not self.accepted_retry
                if self.needs_restart:
                    self.restart()
                self.verify()
            else:
                if self.needs_restart:
                    require(self.applied and self.state.get('activation_started'), 'Interrupted base recovery lacks migration/activation evidence.')
                    self.activation_started = True
                    self.restart(); self.verify(BASE); self.before_service = self.service()
                self.guard()
                self.activate()
                self.verify()
            self.completed = True; self.state['complete'] = True; self.save('DEPLOYED_VERIFIED')
            say('BOOKING_ROUTE_BACKEND_DEPLOYED_VERIFIED')
            say('BACKEND_SHA='+APP_SHA)
            say('EXISTING_COMPLETED_JOURNEY_AND_STRIPE_CONFIGURATION_PRESERVED')
        except BaseException:
            if self.state:
                self.log_failure('failure')
                try:
                    self.recover()
                except BaseException:
                    self.log_failure('recovery-failure')
                    raise Stop('Recovery could not be verified; inspect the private receipt before any retry.') from None
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deploy', action='store_true', required=True)
    parser.parse_args(argv)
    os.umask(0o077)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    def interrupted(signum, frame):
        raise Stop('Execution interrupted; inspect the private recovery receipt.')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    require(os.geteuid() == 0, 'Run in the approved root Hostinger session.')
    descriptor = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop('Another backend deployment holds the existing release lock.')
        Rollout().execute()
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        say('STOP: '+str(error) if isinstance(error, Stop) else 'STOP: '+type(error).__name__+'; inspect the private record.')
        raise SystemExit(1)
