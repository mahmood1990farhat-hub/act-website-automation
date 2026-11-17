#!/usr/bin/env python3
"""Preservation-guarded ACT TEST frontend release retry (no automatic reruns).

--check is read-only. --activate requires a NEW explicit owner approval after
review of the old failure, plus the existing interactive release approval.
The previous failed private record is never modified or deleted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True

OLD_ATTEMPT = Path('/root/act-release-backup/stripe-frontend-activation-20261117')
RETRY_ATTEMPT = Path('/root/act-release-backup/stripe-frontend-activation-20261117-retry1')
RELEASE_SCRIPT = Path('/root/act-stripe-readonly/activate_stripe_frontend_retry.py')
RELEASE_SHA256 = '977cd47f5174f78ccf0041eba1982c88106a2aac7d25fce422c5ab72696de0e3'
SITE = Path('/etc/nginx/sites-enabled/airportandcitytransfer')
PM2_DUMP = Path('/home/act/.pm2/dump.pm2')
FRONTEND_SOURCE = '02e59f95b5fd85d6ad07e881f3f2671a01a7bd65'
BACKEND_SOURCE = 'd77e896af9daca5a39b7a85d5b76c5821e008d23'

MUST_EXIST = (
    'RELEASE_PREPARATION_STARTED.json', 'nginx.before.conf',
    'nginx.proposed.conf', 'pm2.before.json', 'candidate.plan.json',
)
MUST_NOT_EXIST = (
    'nginx.rollback.conf', 'BOTH_NGINX_CONFIGS_VALIDATED.json',
    'PM2_START_STARTED.json', 'CANDIDATE_HTTP_READY.json',
    'PM2_DUMP_UPDATE_STARTED.json', 'PM2_CANDIDATE_PERSISTED.json',
    'NGINX_FRONTEND_SWITCH_STARTED.json', 'NGINX_RELOAD_STARTED.json',
    'FRONTEND_STRIPE_TEST_KEY_ACTIVATED.json', 'FRONTEND_RETURNED_TO_3004.json',
    'ROLLBACK_STARTED.json',
)


class Stop(Exception):
    """Only stable, non-sensitive status codes are allowed."""


def need(value, code):
    if not value:
        raise Stop(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def private_file(path, uid, max_size=1024 * 1024):
    need(not path.is_symlink(), 'PREVIOUS_RECORD_FILE_LINK')
    info = path.stat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
         and info.st_size <= max_size and not stat.S_IMODE(info.st_mode) & 0o077,
         'PREVIOUS_RECORD_FILE_NOT_PRIVATE')
    return path.read_bytes()


def inspect_previous(*, uid=0):
    need(OLD_ATTEMPT.is_dir() and not OLD_ATTEMPT.is_symlink(),
         'PREVIOUS_FAILED_RECORD_NOT_FOUND')
    folder = OLD_ATTEMPT.stat()
    need(folder.st_uid == uid and stat.S_ISDIR(folder.st_mode)
         and not stat.S_IMODE(folder.st_mode) & 0o077,
         'PREVIOUS_FAILED_RECORD_NOT_PRIVATE')
    need(not RETRY_ATTEMPT.exists() and not RETRY_ATTEMPT.is_symlink(),
         'RETRY_RECORD_ALREADY_EXISTS_NO_OVERWRITE')
    for name in MUST_NOT_EXIST:
        need(not (OLD_ATTEMPT / name).exists() and
             not (OLD_ATTEMPT / name).is_symlink(),
             'PREVIOUS_ATTEMPT_PROGRESS_NOT_EXPECTED')
    saved = {name: private_file(OLD_ATTEMPT / name, uid) for name in MUST_EXIST}
    try:
        marker = json.loads(saved['RELEASE_PREPARATION_STARTED.json'])
        plan = json.loads(saved['candidate.plan.json'])
    except (ValueError, TypeError):
        raise Stop('PREVIOUS_FAILURE_RECEIPT_UNREADABLE') from None
    need(isinstance(marker, dict) and marker.get('status') == 'RELEASE_PREPARATION_STARTED'
         and marker.get('payment_attempted') is False and marker.get('backend_modified') is False,
         'PREVIOUS_FAILURE_MARKER_MISMATCH')
    need(isinstance(plan, dict) and plan.get('activated') is False
         and plan.get('frontend_source') == FRONTEND_SOURCE
         and plan.get('backend_source') == BACKEND_SOURCE
         and plan.get('old_nginx_sha256') == sha(saved['nginx.before.conf'])
         and plan.get('proposed_nginx_sha256') == sha(saved['nginx.proposed.conf'])
         and plan.get('old_pm2_sha256') == sha(saved['pm2.before.json']),
         'PREVIOUS_FAILURE_PLAN_MISMATCH')
    need(SITE.is_symlink(), 'LIVE_NGINX_SITE_IDENTITY_CHANGED')
    site = SITE.resolve(strict=True)
    need(site.is_relative_to(Path('/etc/nginx')) and
         site.read_bytes() == saved['nginx.before.conf'],
         'LIVE_SITE_NOT_PREVIOUS_PREIMAGE')
    need(PM2_DUMP.is_file() and not PM2_DUMP.is_symlink() and
         PM2_DUMP.read_bytes() == saved['pm2.before.json'],
         'PM2_SAVED_STATE_NOT_PREVIOUS_PREIMAGE')


def load_corrected_release():
    need(RELEASE_SCRIPT.is_file() and not RELEASE_SCRIPT.is_symlink(),
         'CORRECTED_RELEASE_SCRIPT_MISSING')
    need(sha(RELEASE_SCRIPT.read_bytes()) == RELEASE_SHA256,
         'CORRECTED_RELEASE_SCRIPT_HASH_MISMATCH')
    spec = importlib.util.spec_from_file_location('act_stripe_retry_release_pinned', RELEASE_SCRIPT)
    need(spec is not None and spec.loader is not None,
         'CORRECTED_RELEASE_MODULE_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop('ONLY_CHECK_OR_SEPARATELY_APPROVED_RETRY_ACCEPTED')


def main(argv=None):
    try:
        parser = SafeParser(description=__doc__)
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument('--check', action='store_true')
        modes.add_argument('--activate', action='store_true')
        args = parser.parse_args(argv)
        need(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
        inspect_previous()
        release = load_corrected_release()
        need(release.RECORD == OLD_ATTEMPT,
             'ORIGINAL_ACTIVATION_RECORD_PATH_CHANGED')
        release.RECORD = RETRY_ATTEMPT
        if args.check:
            result = release.main(['--check'])
            if result == 0:
                print('PASS: FAILED_ATTEMPT_PRESERVED_AND_NEW_RETRY_RECORD_AVAILABLE')
                print('NO_CHANGES; RETRY_NOT_AUTHORISED')
            return result
        # An explicit owner retry approval is needed before this path is invoked.
        # The pinned underlying helper independently requires its live TTY phrase.
        return release.main(['--activate'])
    except Stop as error:
        print('STOPPED: ' + str(error) + '; NO_NEW_RETRY', file=sys.stderr)
        return 1
    except Exception:
        print('STOPPED: RETRY_PRESERVATION_CHECK_UNAVAILABLE; NO_NEW_RETRY',
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
