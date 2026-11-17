#!/usr/bin/env python3
"""ACT Trip #35 confirmation recovery; exact-owner-approved one-time action.

--check: reads filesystem/service/Trip35 only.
--apply: one directory-only permission repair then ONE synchronous call to
already-deployed paid-booking-confirmation task, with no Celery publication.
--status: read-only recovery marker/Trip status (does not resend).
No frontend/backend restart, Stripe action, queue drain, or SMTP probe.
"""
from __future__ import annotations

import argparse
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys
sys.dont_write_bytecode = True

BACK = Path('/var/www/atg/atg-backend')
CURRENT = BACK / 'current'
RELEASES = BACK / 'releases'
RECORD = Path('/root/act-release-backup/trip35-confirmation-recovery-20261117')
LOCK = Path('/run/lock/act-backend-deploy.lock')
EXPECTED_CURRENT_SHA = 'd77e896af9daca5a39b7a85d5b76c5821e008d23'
EXPECTED_WORKER_SHA = '82c0b14ad2a71e1ce3d8d1df3527431b698ac461'
TASK_BLOB = 'c057119f83cd92bffb920ad85216026a4099c21c'
PDF_BLOB = '8cbc75d42d43922200d77979ca501c7670010090'
TRIP = 35
PI = 'pi_3UcuauBxjYEaMc5N08BDzj38'
PHRASE = 'APPROVE ACT TRIP 35 PDF AND TWO TEST EMAILS'


class Stop(Exception):
    """Only safe, fixed error codes; never print exceptions or credentials."""


def require(ok, code):
    if not ok:
        raise Stop(code)


def command(argv, *, env=None, cwd=None, timeout=25):
    try:
        return subprocess.run([str(a) for a in argv], env=env, cwd=cwd,
                              capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise Stop('GUARDED_SUBPROCESS_UNAVAILABLE') from None


def safe_json(path):
    require(path.is_file() and not path.is_symlink(), 'RELEASE_RECEIPT_NOT_REGULAR')
    return json.loads(path.read_bytes())


def git_blob(path):
    require(path.is_file() and not path.is_symlink(), 'REVIEWED_SOURCE_UNAVAILABLE')
    content = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()


def systemd(name):
    result = command(['/usr/bin/systemctl', 'show', name,
                      '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState'], timeout=8)
    require(result.returncode == 0, 'SERVICE_IDENTITY_UNAVAILABLE')
    return dict(line.split('=', 1) for line in result.stdout.decode('utf-8', 'replace').splitlines()
                if '=' in line)


def worker_snapshot():
    svc = systemd('act-celery-confirmations.service')
    require(svc.get('ActiveState') == 'active' and svc.get('SubState') == 'running',
            'CONFIRMATION_WORKER_NOT_RUNNING')
    pid = int(svc.get('MainPID') or 0)
    require(pid > 1, 'WORKER_PID_UNAVAILABLE')
    proc = Path(f'/proc/{pid}')
    require(proc.stat().st_uid == pwd.getpwnam('www-data').pw_uid,
            'CONFIRMATION_WORKER_NOT_WWW_DATA')
    args = (proc / 'cmdline').read_bytes().split(b'\0')
    require(b'--queues=act_booking_confirmations' in args or
            (b'--queues' in args and args.index(b'--queues') + 1 < len(args)
             and args[args.index(b'--queues') + 1] == b'act_booking_confirmations'),
            'WORKER_WRONG_QUEUE')
    root = (proc / 'cwd').resolve(strict=True)
    require(root.is_relative_to(RELEASES.resolve(strict=True)), 'WORKER_OUTSIDE_ACT_RELEASES')
    require(safe_json(root / 'release.json').get('git_sha') == EXPECTED_WORKER_SHA,
            'WORKER_RELEASE_CHANGED')
    return root


def resolve_storage(current, worker):
    current_media = current / 'media'
    worker_media = worker / 'media'
    require(current_media.is_symlink() and worker_media.is_symlink(),
            'EXPECTED_SHARED_MEDIA_SYMLINKS')
    m1 = current_media.resolve(strict=True)
    m2 = worker_media.resolve(strict=True)
    require(m1 == m2 and m1.is_dir(), 'MEDIA_NOT_SHARED')
    require(m1.is_relative_to(BACK.resolve(strict=True)) and
            not m1.is_relative_to(RELEASES.resolve(strict=True)),
            'MEDIA_OUTSIDE_SAFE_SHARED_BACKEND_ROOT')
    a = current / 'media/trips/booking_confirmations'
    b = worker / 'media/trips/booking_confirmations'
    target = a.resolve(strict=True)
    require(target == b.resolve(strict=True), 'BOOKING_PDF_DIRECTORY_NOT_SHARED')
    require(target.is_dir() and not a.is_symlink() and not b.is_symlink()
            and not target.is_symlink() and target.parent == m1 / 'trips',
            'BOOKING_PDF_DIRECTORY_IDENTITY_CHANGED')
    return target


def can_write(target):
    result = command(['/usr/sbin/runuser', '-u', 'www-data', '--',
                      '/usr/bin/test', '-w', target], timeout=8)
    return result.returncode == 0


def source_and_directory_snapshot():
    require(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
    require(CURRENT.is_symlink(), 'BACKEND_CURRENT_POINTER_CHANGED')
    current = CURRENT.resolve(strict=True)
    require(current.is_relative_to(RELEASES.resolve(strict=True)) and
            safe_json(current / 'release.json').get('git_sha') == EXPECTED_CURRENT_SHA,
            'ACTIVE_BACKEND_RELEASE_CHANGED')
    worker = worker_snapshot()
    for root in (current, worker):
        require(git_blob(root / 'apps/payments/tasks.py') == TASK_BLOB,
                'CONFIRMATION_TASK_SOURCE_DRIFT')
        require(git_blob(root / 'apps/trips/services/booking_confirmation.py') == PDF_BLOB,
                'BOOKING_PDF_HELPER_SOURCE_DRIFT')
    target = resolve_storage(current, worker)
    details = target.stat()
    require(details.st_uid == 0 and details.st_gid == 0 and
            stat.S_IMODE(details.st_mode) == 0o755 and details.st_nlink >= 2,
            'BOOKING_PDF_PERMISSION_BASELINE_CHANGED')
    require(not can_write(target), 'PDF_STORAGE_ALREADY_WRITABLE_STOP')
    require(LOCK.is_file() and not LOCK.is_symlink(), 'BACKEND_RELEASE_LOCK_MISSING')
    require(not RECORD.exists() and not RECORD.is_symlink(),
            'TRIP35_RECOVERY_ALREADY_STARTED_NO_RETRY')
    return current, worker, target, details


DJANGO_READ = r'''
from django.conf import settings
from django.core.validators import validate_email
from apps.trips.models import Trip
from django.db import transaction
with transaction.atomic():
    t = Trip.objects.get(pk=35)
    assert t.is_guest_checkout is True and t.is_paid is True
    assert t.stripe_payment_intent == 'pi_3UcuauBxjYEaMc5N08BDzj38'
    assert t.passenger_confirmation_sent_at is None
    assert t.internal_booking_notification_sent_at is None
    assert not t.booking_confirmation_pdf
    for address in (t.passenger_email, settings.ADMIN_EMAIL, settings.EMAIL_HOST_USER):
        validate_email(address)
    assert settings.EMAIL_HOST and settings.EMAIL_HOST_PASSWORD
print('PASS: EXACT_PAID_GUEST_TRIP_35_AND_SMTP_CONFIG_CHECKED')
'''

DJANGO_SEND = r'''
from apps.trips.models import Trip
from apps.payments.tasks import deliver_paid_booking_confirmations
from django.conf import settings
from django.core.validators import validate_email
from django.db import transaction
with transaction.atomic():
    t = Trip.objects.select_for_update(of=('self',)).get(pk=35)
    assert t.is_guest_checkout is True and t.is_paid is True
    assert t.stripe_payment_intent == 'pi_3UcuauBxjYEaMc5N08BDzj38'
    assert t.passenger_confirmation_sent_at is None
    assert t.internal_booking_notification_sent_at is None
    assert not t.booking_confirmation_pdf
    for address in (t.passenger_email, settings.ADMIN_EMAIL, settings.EMAIL_HOST_USER):
        validate_email(address)
assert deliver_paid_booking_confirmations.request.called_directly is True
try:
    result = deliver_paid_booking_confirmations.run(35)
except Exception as exc:
    print('TRIP35_FAILURE_CLASS:', type(exc).__name__)
    raise
t = Trip.objects.get(pk=35)
assert t.booking_confirmation_pdf and t.passenger_confirmation_sent_at and t.internal_booking_notification_sent_at
assert result.get('trip_id') == 35 and result.get('pdf_ready') is True
print('PASS: TRIP35_PDF_AND_BOTH_SMTP_ACCEPTANCE_MARKERS')
'''

DJANGO_STATUS = r'''
from apps.trips.models import Trip
t = Trip.objects.get(pk=35)
assert t.is_guest_checkout is True and t.is_paid is True
assert t.stripe_payment_intent == 'pi_3UcuauBxjYEaMc5N08BDzj38'
print('PDF_READY:', bool(t.booking_confirmation_pdf))
print('PASSENGER_EMAIL_RECORDED:', bool(t.passenger_confirmation_sent_at))
print('ADMIN_EMAIL_RECORDED:', bool(t.internal_booking_notification_sent_at))
'''


def django(current, source, *, readonly, timeout=90):
    # Systemd supplies the ACT environment to the running backend process.
    # Use its actual current environment without displaying or persisting it.
    # The shared .env file may not be directly readable by www-data.
    svc = systemd('act.service')
    require(svc.get('ActiveState') == 'active', 'BACKEND_SERVICE_NOT_ACTIVE')
    pid = int(svc.get('MainPID') or 0)
    require(pid > 1 and (Path(f'/proc/{pid}/cwd').resolve(strict=True) == current),
            'BACKEND_SERVICE_RELEASE_CHANGED')
    env = {
        'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        'LANG': 'C.UTF-8',
        'PYTHONDONTWRITEBYTECODE': '1',
    }
    procenv = (Path(f'/proc/{pid}') / 'environ').read_bytes()
    for entry in procenv.split(b'\0'):
        if b'=' not in entry:
            continue
        raw_key, raw_value = entry.split(b'=', 1)
        key = raw_key.decode('utf-8', 'surrogateescape')
        if key in {'PATH', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP',
                   'BASH_ENV', 'ENV', 'HOME', 'USER', 'LOGNAME', 'PGOPTIONS'} or key.startswith('LD_'):
            continue
        env[key] = raw_value.decode('utf-8', 'surrogateescape')
    if readonly:
        env['PGOPTIONS'] = '-c default_transaction_read_only=on'
    # No stdout/stderr from Django (or SMTP) is emitted to the terminal.
    return command(['/usr/sbin/runuser', '-u', 'www-data', '--',
                    current / '.venv/bin/python', '-B', 'manage.py', 'shell', '-c', source],
                   env=env, cwd=current, timeout=timeout)


def write_new(path, content):
    with path.open('xb') as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def mark(state):
    write_new(RECORD / (state + '.json'), json.dumps({'state': state, 'trip_id': TRIP,
                                                     'payment_intent_id': PI}, sort_keys=True).encode())


def grant_storage(target, original):
    acl = shutil.which('setfacl')
    if acl:
        getacl = shutil.which('getfacl')
        require(getacl is not None, 'ACL_BACKUP_TOOL_UNAVAILABLE')
        before = command([getacl, '-p', target], timeout=8)
        require(before.returncode == 0, 'ACL_BASELINE_UNAVAILABLE')
        write_new(RECORD / 'original-directory.acl', before.stdout)
        result = command([acl, '-m', 'u:www-data:rwx', target], timeout=12)
        require(result.returncode == 0, 'PDF_DIRECTORY_ACL_UPDATE_FAILED')
        method = 'ACL_USER_WWW_DATA'
    else:
        www_group = grp.getgrnam('www-data').gr_gid
        os.chown(target, -1, www_group)
        os.chmod(target, 0o2775)
        method = 'GROUP_WWW_DATA_SETGID'
    after = target.stat()
    require(after.st_uid == original.st_uid and
            not (stat.S_IMODE(after.st_mode) & 0o002) and
            can_write(target), 'PDF_DIRECTORY_REPAIR_NOT_VERIFIED')
    mark('PDF_STORAGE_WRITE_ACCESS_GRANTED')
    return method


def check():
    current, worker, target, metadata = source_and_directory_snapshot()
    result = django(current, DJANGO_READ, readonly=True, timeout=25)
    require(result.returncode == 0 and
            b'PASS: EXACT_PAID_GUEST_TRIP_35_AND_SMTP_CONFIG_CHECKED' in result.stdout,
            'TRIP35_OR_SMTP_READ_ONLY_PREFLIGHT_FAILED')
    print('PASS: TRIP35_PAID_GUEST_AND_EMAIL_RECIPIENTS_READY')
    print('PASS: EXACT_SHARED_PDF_DIRECTORY_ROOT_OWNED_NOT_WRITABLE')
    print('PASS: CONFIRMATION_TASK_MATCHES_REVIEWED_BACKEND')
    print('NO_CHANGES; NO_EMAILS_SENT')
    return current, target, metadata


def apply():
    require(sys.stdin.isatty() and sys.stderr.isatty(),
            'ROOT_INTERACTIVE_OWNER_TERMINAL_REQUIRED')
    # Ensure no production side effects before the owner types the phrase.
    current, target, metadata = check()
    if input('Enter approved ACT Trip 35 recovery phrase: ').strip() != PHRASE:
        raise Stop('APPROVAL_PHRASE_DIFFERENT_NO_CHANGES')
    with LOCK.open('rb') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop('BACKEND_RELEASE_LOCK_BUSY') from None
        # The second preflight is under the existing release lock.
        current, target, metadata = check()
        RECORD.mkdir(mode=0o700)
        os.chmod(RECORD, 0o700)
        write_new(RECORD / 'prechange-directory.json', json.dumps({
            'target': str(target), 'owner_uid': metadata.st_uid,
            'group_gid': metadata.st_gid, 'mode': oct(stat.S_IMODE(metadata.st_mode)),
            'current_backend_sha': EXPECTED_CURRENT_SHA,
            'running_worker_sha': EXPECTED_WORKER_SHA,
            'trip_id': TRIP,
        }, sort_keys=True).encode())
        mark('REPAIR_STARTED')
        method = grant_storage(target, metadata)
        print('PASS: ONLY_SHARED_BOOKING_PDF_DIRECTORY_ACCESS_REPAIRED')
        print('PDF_PERMISSION_METHOD:', method)
        # An exclusive one-shot marker precedes all external mail sending.
        mark('TRIP35_EMAIL_RECOVERY_ATTEMPT_STARTED')
        result = django(current, DJANGO_SEND, readonly=False, timeout=120)
        if result.returncode != 0 or b'PASS: TRIP35_PDF_AND_BOTH_SMTP_ACCEPTANCE_MARKERS' not in result.stdout:
            mark('RECOVERY_UNVERIFIED_NO_RETRY')
            match = re.search(rb'(?m)^TRIP35_FAILURE_CLASS: ([A-Za-z][A-Za-z0-9_]{0,80})$', result.stdout)
            print('RECOVERY_FAILURE_CLASS:', match.group(1).decode() if match else 'UNAVAILABLE')
            print('STOPPED: TRIP35_RECOVERY_UNVERIFIED; DO_NOT_REPEAT_EMAIL_SEND')
            return 2
        mark('RECOVERY_REPORTED_SMTP_ACCEPTED')
        print('PASS: TRIP35_BOOKING_PDF_AND_BOTH_EMAILS_SMTP_ACCEPTED')
        print('NO_NEW_BOOKING_OR_PAYMENT; NO_QUEUE_CHANGES')
        return 0


def status():
    require(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
    require(CURRENT.is_symlink(), 'BACKEND_CURRENT_POINTER_CHANGED')
    current = CURRENT.resolve(strict=True)
    proc = django(current, DJANGO_STATUS, readonly=True, timeout=25)
    require(proc.returncode == 0, 'TRIP35_STATUS_CHECK_UNAVAILABLE')
    # Output only the three fixed booleans; ignore all other process output.
    for label in ('PDF_READY:', 'PASSENGER_EMAIL_RECORDED:', 'ADMIN_EMAIL_RECORDED:'):
        matched = re.search(rb'(?m)^' + label.encode() + rb' (True|False)$', proc.stdout)
        require(matched is not None, 'TRIP35_STATUS_CHECK_INCOMPLETE')
        print(label, matched.group(1).decode())
    print('READ_ONLY_NO_CHANGES')


def main(argv=None):
    try:
        p = argparse.ArgumentParser(description=__doc__)
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument('--check', action='store_true')
        g.add_argument('--apply', action='store_true')
        g.add_argument('--status', action='store_true')
        args = p.parse_args(argv)
        os.umask(0o077)
        if args.check:
            check()
            return 0
        if args.apply:
            return apply()
        status()
        return 0
    except Stop as err:
        print('STOPPED: ' + str(err) + '; NO_AUTOMATIC_RETRY', file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        print('STOPPED: TRIP35_GUARDED_OPERATION_UNAVAILABLE; DO_NOT_REPEAT', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
