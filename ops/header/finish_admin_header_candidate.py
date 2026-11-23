#!/usr/bin/env python3
"""Finish the approved ACT Admin link using the existing, running candidate.

No installation, build, PM2 start/removal, service restart or key change occurs.
The failed attempt stays immutable. --finish is one guarded continuation;
--status reads only this continuation's private journal.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys

sys.dont_write_bytecode = True
BASE_SHA256 = '461583a79fa8ab3b692ea394e3aeab225a0a167d969df1ceb769ab151f425f10'
COMPLETION_RECORD = Path('/root/act-release-backup/admin-header-4c69a03-20261123-finish')
EXPECTED_ATTEMPT_STAGES = frozenset({
    'PREPARATION_STARTED', 'CANDIDATE_BUILT_AND_CONFIGS_VALIDATED', 'CANDIDATE_START_ATTEMPTED',
})
STAGES = (
    'COMPLETION_STARTED', 'EXISTING_CANDIDATE_VERIFIED', 'PM2_DUMP_WRITE_ATTEMPTED',
    'CANDIDATE_PERSISTED', 'NGINX_SWITCH_ATTEMPTED', 'NGINX_RELOAD_ATTEMPTED',
    'ADMIN_HEADER_DEPLOYED', 'COMPLETION_STOPPED_BEFORE_WRITES', 'ROLLBACK_STARTED',
    'PREVIOUS_FRONTEND_RESTORED',
)


class Stop(Exception):
    """Fixed, non-secret messages only."""


def need(value, message):
    if not value:
        raise Stop(message)


def emit(message):
    try:
        print(message, flush=True)
    except (BrokenPipeError, OSError):
        pass


def load_base():
    path = Path(__file__).resolve().with_name('admin_header_release.py')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
         and hashlib.sha256(path.read_bytes()).hexdigest() == BASE_SHA256,
         'PINNED_ADMIN_HEADER_HELPER_DIFFERS')
    spec = importlib.util.spec_from_file_location('act_header_completion_base', path)
    need(spec is not None and spec.loader is not None, 'ADMIN_HEADER_HELPER_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def private_directory(path):
    info = path.lstat()
    need(stat.S_ISDIR(info.st_mode) and path.resolve(strict=True) == path
         and info.st_uid == 0 and not info.st_mode & 0o077, 'PRIVATE_RECORD_INVALID')


def attempt_stages(base, record):
    found = set()
    for stage in base.STAGES:
        path = record / (stage + '.json')
        if path.exists() or path.is_symlink():
            value = json.loads(base.regular(path))
            need(value.get('state') == stage and value.get('patch_sha') == base.PATCH_SHA
                 and all(value.get(field) is False for field in
                         ('backend_modified', 'credentials_changed', 'payment_attempted')),
                 'ORIGINAL_ATTEMPT_JOURNAL_INVALID')
            found.add(stage)
    need(found == EXPECTED_ATTEMPT_STAGES, 'ORIGINAL_ATTEMPT_STAGE_CHANGED')
    return found


def merged_assets(old, candidate):
    result = dict(old)
    for name, value in candidate.items():
        need(name not in result or result[name] == value, 'EXISTING_ASSET_COLLISION')
        result[name] = value
    return dict(sorted(result.items()))


def validate_plan(base, plan, source, expected_source, public, original, proposed, rollback, new_build):
    expected = {
        'patch_sha': base.PATCH_SHA, 'source_basis': str(base.ACTIVE),
        'source_basis_sha256': base.digest(base.packed(source)),
        'candidate_source_sha256': base.digest(base.packed(expected_source)),
        'old_build_id': base.OLD_BUILD, 'new_build_id': new_build,
        'candidate': str(base.CANDIDATE), 'assets': str(base.NEW_ASSETS),
        'name': base.NAME, 'port': base.PORT,
        'original_nginx_sha256': base.digest(original),
        'proposed_nginx_sha256': base.digest(proposed),
        'rollback_nginx_sha256': base.digest(rollback),
        'public_environment_sha256': base.digest(base.packed(public)),
        'credentials_changed': False, 'source_is_active_copy_plus_approved_patch': True,
    }
    need(all(plan.get(key) == value for key, value in expected.items()), 'ORIGINAL_PLAN_MISMATCH')
    need(isinstance(plan.get('backend'), dict), 'ORIGINAL_BACKEND_BASELINE_MISSING')


def validate_saved_rows(base, prior, rows, saved):
    need(isinstance(saved, list) and saved and rows, 'SAVED_PM2_INVENTORY_INVALID')
    saved_names, live_names = [r['name'] for r in saved], [r['name'] for r in rows]
    need(len(set(saved_names)) == len(saved_names) and len(set(live_names)) == len(live_names)
         and base.NAME not in saved_names and set(live_names) == set(saved_names) | {base.NAME},
         'PM2_INVENTORY_CHANGED')
    retained = []
    for saved_row in saved:
        row = prior.one(rows, saved_row['name'])
        need(all(row['pm2_env'].get(key) == saved_row.get(key) for key in prior.LAUNCH),
             'RETAINED_PM2_LAUNCH_CHANGED')
        retained.append(row)
    return retained


def completion_class(base):
    """Bind only after verifying the sibling helper's exact source hash."""
    class Completion(base.Release):
        def listener(self, port, row, directory):
            raw = self.command('existing-listener', ['/usr/bin/ss', '-H', '-ltnp', f'sport = :{port}'])
            need(row.get('pid', 0) > 1 and row['pm2_env'].get('status') == 'online'
                 and set(re.findall(rb'pid=(\d+)', raw)) == {str(row['pid']).encode()}
                 and Path(f'/proc/{row["pid"]}/cwd').resolve(strict=True) == directory,
                 'EXISTING_LISTENER_IDENTITY_CHANGED')

        def candidate_environment(self, row):
            # Preserve the reviewed expected-value contract. PM2-added entries
            # are captured in the fresh full launch/identity snapshot below.
            self.verify_candidate_row(row, healthy=False)

        def adopt_existing(self):
            need(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
            need(not COMPLETION_RECORD.exists() and not COMPLETION_RECORD.is_symlink(),
                 'COMPLETION_ALREADY_ATTEMPTED_USE_STATUS')
            private_directory(base.RECORD)
            attempt_stages(base, base.RECORD)
            self.original_record = self.prior.tree(base.RECORD)
            self.plan = json.loads(base.regular(base.RECORD / 'plan.json'))
            for path in (base.ACTIVE, base.CANDIDATE, base.OLD_ASSETS, base.NEW_ASSETS):
                need(path.is_dir() and path.resolve(strict=True) == path, 'EXISTING_RELEASE_PATH_CHANGED')
            self.original = base.regular(base.RECORD / 'nginx.before.conf')
            need(base.digest(self.original) == base.SITE_HASH, 'ORIGINAL_NGINX_SNAPSHOT_CHANGED')
            self.proposed, self.rollback_config = base.route_pair(self.original)
            need(base.regular(base.RECORD / 'nginx.proposed.conf') == self.proposed
                 and base.regular(base.RECORD / 'nginx.rollback.conf') == self.rollback_config,
                 'ORIGINAL_ROUTING_PLAN_CHANGED')
            self.site = base.SITE.resolve(strict=True)
            need(self.site.is_relative_to(Path('/etc/nginx')) and base.regular(self.site) == self.original,
                 'PUBLIC_ROUTING_ALREADY_CHANGED')
            self.original_dump = base.regular(base.RECORD / 'pm2.before.json')
            need(base.regular(base.DUMP) == self.original_dump, 'SAVED_PM2_DUMP_CHANGED')
            self.saved_list = json.loads(self.original_dump)
            self.source = json.loads(base.regular(base.RECORD / 'source.before.json'))
            need(base.source_tree(base.ACTIVE) == self.source, 'ORIGINAL_SOURCE_CHANGED')
            self.expected_source = dict(self.source)
            for locale in base.LABELS:
                relative = f'src/dictionaries/{locale}/home.json'
                need(self.source.get(relative) == base.MENU_BEFORE[locale], 'ORIGINAL_MENU_CHANGED')
                self.expected_source[relative] = base.MENU_AFTER[locale]
            need(base.source_tree(base.CANDIDATE) == self.expected_source, 'EXISTING_CANDIDATE_SOURCE_CHANGED')
            self.old_build = base.regular(base.ACTIVE / '.next/BUILD_ID').decode().strip()
            self.new_build = base.regular(base.CANDIDATE / '.next/BUILD_ID').decode().strip()
            need(self.old_build == base.OLD_BUILD and self.new_build != self.old_build
                 and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.new_build), 'EXISTING_BUILD_ID_CHANGED')
            self.public = json.loads(base.regular(base.RECORD / 'public-environment.json'))
            for root in (base.ACTIVE, base.CANDIDATE):
                base.validate_public(self.public, base.compiled_keys(root))
            validate_plan(base, self.plan, self.source, self.expected_source, self.public,
                          self.original, self.proposed, self.rollback_config, self.new_build)
            self.backend_baseline = self.plan['backend']
            need(self.backend() == self.backend_baseline, 'ORIGINAL_BACKEND_CHANGED')
            rows = self.rows()
            retained = validate_saved_rows(base, self.prior, rows, self.saved_list)
            active = [r for r in retained if r['pm2_env'].get('pm_cwd') == str(base.ACTIVE)]
            need(len(active) == 1, 'RETAINED_ACTIVE_FRONTEND_AMBIGUOUS')
            live_current = active[0]
            saved_current = self.prior.one(self.saved_list, live_current['name'])
            # Expected candidate settings come from the immutable original dump.
            self.current = {'name': live_current['name'], 'pid': live_current['pid'],
                            'pm2_env': copy.deepcopy(saved_current)}
            need(self.public_environment(live_current) == self.public, 'ORIGINAL_PUBLIC_CONFIGURATION_CHANGED')
            candidate = self.prior.one(rows, base.NAME)
            self.verify_candidate_row(candidate)
            self.candidate_environment(candidate)
            self.listener(3005, live_current, base.ACTIVE)
            self.listener(base.PORT, candidate, base.CANDIDATE)
            # These are fresh continuation identities, not invented old PID receipts.
            self.ids = [self.prior.identity(row) for row in retained]
            self.candidate_identity = self.prior.identity(candidate)
            self.candidate_launch = {key: copy.deepcopy(candidate['pm2_env'].get(key)) for key in self.prior.LAUNCH}
            self.assets_before = self.prior.tree(base.OLD_ASSETS)
            self.candidate_assets = self.prior.tree(base.CANDIDATE / '.next/static')
            self.assets_new = merged_assets(self.assets_before, self.candidate_assets)
            need(self.prior.tree(base.NEW_ASSETS) == self.assets_new, 'EXISTING_ASSET_UNION_CHANGED')
            self.master_hash = base.digest(base.regular(base.MASTER))
            self.entries = sorted(base.SITE.parent.iterdir())
            self.other_nginx_hash = self.other_nginx()
            self.lock_identity = (base.LOCK.stat().st_dev, base.LOCK.stat().st_ino)
            self.guard(self.original, candidate=True)

        def guard(self, expected_route, candidate=None):
            rows = super().guard(expected_route, candidate=candidate)
            need(self.prior.tree(base.RECORD) == self.original_record, 'ORIGINAL_ATTEMPT_RECORD_CHANGED')
            need(base.source_tree(base.CANDIDATE) == self.expected_source
                 and base.regular(base.CANDIDATE / '.next/BUILD_ID').decode().strip() == self.new_build
                 and self.prior.tree(base.CANDIDATE / '.next/static') == self.candidate_assets
                 and self.prior.tree(base.NEW_ASSETS) == self.assets_new, 'EXISTING_CANDIDATE_ARTIFACT_CHANGED')
            owned = self.prior.one(rows, base.NAME)
            self.candidate_environment(owned)
            need(all(owned['pm2_env'].get(key) == value for key, value in self.candidate_launch.items()),
                 'EXISTING_CANDIDATE_LAUNCH_CHANGED')
            if candidate is True:
                need(self.prior.identity(owned) == self.candidate_identity, 'EXISTING_CANDIDATE_RUNTIME_CHANGED')
                self.listener(base.PORT, owned, base.CANDIDATE)
            self.listener(3005, self.prior.one(rows, self.current['name']), base.ACTIVE)
            return rows

        def begin_record(self):
            self.guard(self.original, candidate=True)
            need(base.regular(base.DUMP) == self.original_dump, 'SAVED_PM2_DUMP_CHANGED')
            COMPLETION_RECORD.mkdir(mode=0o700)
            self.work = COMPLETION_RECORD
            self.journal('COMPLETION_STARTED')
            copied = self.work / 'original-attempt'
            copied.mkdir(mode=0o700)
            for relative, expected in self.original_record.items():
                need('/' not in relative, 'UNEXPECTED_ORIGINAL_RECORD_SUBDIRECTORY')
                raw = base.regular(base.RECORD / relative)
                need(base.digest(raw) == expected, 'ORIGINAL_ATTEMPT_RECORD_CHANGED')
                base.write_new(copied / relative, raw)
            for name, raw in [('nginx.before.conf', self.original), ('nginx.proposed.conf', self.proposed),
                              ('nginx.rollback.conf', self.rollback_config), ('pm2.before.json', self.original_dump)]:
                base.write_new(self.work / name, raw)
            base.write_new(self.work / 'continuation-baseline.json', base.packed({
                'patch_sha': base.PATCH_SHA, 'baseline_type': 'fresh_continuation_runtime_snapshot',
                'original_attempt': str(base.RECORD), 'original_record': self.original_record,
                'retained_identities': self.ids, 'candidate_identity': self.candidate_identity,
                'pm2_daemon_identity': self.daemon_identity, 'master_sha256': self.master_hash,
                'other_nginx_sha256': self.other_nginx_hash, 'lock_identity': self.lock_identity,
                'backend_original_baseline': self.backend_baseline,
                'candidate_source': self.expected_source, 'retained_assets': self.assets_before,
                'candidate_assets': self.candidate_assets, 'asset_union': self.assets_new,
                'candidate_rebuilt': False, 'candidate_started': False,
            }))
            for label in ('proposed', 'rollback'):
                full = self.work / f'nginx.{label}.master.conf'
                base.write_new(full, self.prior.validation_master(base.regular(base.MASTER), self.entries,
                                                                 self.work / f'nginx.{label}.conf'))
                self.command('completion-nginx-validate-' + label,
                             ['/usr/sbin/nginx', '-t', '-c', full, '-p', '/etc/nginx/'], log=True)

        def finish(self):
            self.begin_record()
            self.old_pages = self.verify_pages('http://127.0.0.1:3005', self.old_build, base.OLD_ASSETS,
                                               direct=True, has_admin=False)
            self.new_pages = self.verify_pages(f'http://127.0.0.1:{base.PORT}', self.new_build,
                                               base.CANDIDATE / '.next/static', direct=True)
            rows = self.guard(self.original, candidate=True)
            self.journal('EXISTING_CANDIDATE_VERIFIED')
            self.persist(self.prior.one(rows, base.NAME))
            self.switch()

        def rollback(self):
            # The candidate predated this continuation and is never removed.
            if not self.work or self.complete:
                return
            if not self.persisted and not self.switched and not self.reloaded:
                self.journal('COMPLETION_STOPPED_BEFORE_WRITES')
                return
            current = base.regular(self.site)
            need(current in (self.original, self.proposed, self.rollback_config), 'ROLLBACK_NGINX_UNKNOWN')
            self.guard(current, candidate=None)
            current_dump = base.regular(base.DUMP)
            need(current_dump == self.original_dump or
                 (self.new_dump is not None and current_dump == self.new_dump), 'ROLLBACK_PM2_DUMP_UNKNOWN')
            self.journal('ROLLBACK_STARTED')
            target = self.rollback_config if current != self.original or self.reloaded else self.original
            if current != target:
                self.prior.atomic_file(self.site, target, base.digest(current))
            self.command('completion-rollback-nginx-test', ['/usr/sbin/nginx', '-t'], log=True)
            if self.reloaded:
                self.command('completion-rollback-nginx-reload',
                             ['/usr/bin/systemctl', 'reload', 'nginx.service'], log=True)
            if current_dump != self.original_dump:
                self.prior.atomic_file(base.DUMP, self.original_dump, base.digest(current_dump))
            self.guard(target, candidate=None)
            need(base.regular(base.DUMP) == self.original_dump, 'ROLLBACK_PM2_DUMP_NOT_RESTORED')
            if self.reloaded:
                self.verify_public(rollback=True)
            self.journal('PREVIOUS_FRONTEND_RESTORED')
            emit('PREVIOUS_FRONTEND_RESTORED; EXISTING_CANDIDATE_RETAINED; NO_PROCESS_RESTARTS')

    return Completion


def status(base):
    if not COMPLETION_RECORD.exists() and not COMPLETION_RECORD.is_symlink():
        emit('NO_RECORDED_ADMIN_HEADER_COMPLETION_ATTEMPT')
        return
    private_directory(COMPLETION_RECORD)
    found = []
    for stage in STAGES:
        path = COMPLETION_RECORD / (stage + '.json')
        if path.exists() or path.is_symlink():
            value = json.loads(base.regular(path))
            need(value.get('state') == stage and value.get('patch_sha') == base.PATCH_SHA,
                 'COMPLETION_JOURNAL_INVALID')
            found.append(stage)
    emit('RECORDED_ADMIN_HEADER_COMPLETION_STATUS: ' + (found[-1] if found else 'RECORD_CREATED'))
    emit('READ_ONLY_JOURNAL_REPORT; DO_NOT_REPEAT_FINISH')


def main(argv=None):
    base = None
    try:
        args = sys.argv[1:] if argv is None else argv
        need(args in (['--finish'], ['--status']), 'EXPECTED_ONLY_FINISH_OR_STATUS')
        need(os.geteuid() == 0, 'ROOT_VPS_REQUIRED')
        os.umask(0o077)
        base = load_base()
        if args == ['--status']:
            status(base)
            return 0
        prior = base.load_prior()
        need(base.LOCK.is_file() and not base.LOCK.is_symlink(), 'DEPLOYMENT_LOCK_MISSING')
        with base.LOCK.open('rb') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Stop('ANOTHER_DEPLOYMENT_IS_IN_PROGRESS') from None
            held = os.fstat(stream.fileno())
            lock = base.LOCK.lstat()
            held_identity = (held.st_dev, held.st_ino)
            need(stat.S_ISREG(held.st_mode) and stat.S_ISREG(lock.st_mode)
                 and held_identity == (lock.st_dev, lock.st_ino), 'DEPLOYMENT_LOCK_REPLACED')
            release = completion_class(base)(prior)
            release.adopt_existing()
            need(release.lock_identity == held_identity, 'DEPLOYMENT_LOCK_REPLACED')
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            def interrupted(_number, _frame):
                raise Stop('OPERATOR_INTERRUPTED_COMPLETION')
            signal.signal(signal.SIGINT, interrupted)
            signal.signal(signal.SIGTERM, interrupted)
            try:
                release.finish()
            except (Exception, KeyboardInterrupt) as error:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                code = str(error) if isinstance(error, (Stop, base.Stop)) else 'COMPLETION_OPERATION_FAILED'
                try:
                    release.rollback()
                except (Exception, KeyboardInterrupt) as recovery_error:
                    recovery_code = (str(recovery_error) if isinstance(recovery_error, (Stop, base.Stop))
                                     else 'COMPLETION_RECOVERY_FAILED')
                    emit('STOPPED: COMPLETION_RECOVERY_INCOMPLETE; ORIGINAL_CODE=' + code
                         + '; RECOVERY_CODE=' + recovery_code
                         + '; PRESERVE_BOTH_PRIVATE_RECORDS; DO_NOT_REPEAT_FINISH')
                    return 2
                emit('STOPPED: ' + code + '; EXISTING_CANDIDATE_RETAINED; DO_NOT_REPEAT_FINISH')
                return 1
        return 0
    except (Exception, KeyboardInterrupt) as error:
        safe_types = (Stop,) if base is None else (Stop, base.Stop)
        code = str(error) if isinstance(error, safe_types) else 'COMPLETION_PREFLIGHT_UNAVAILABLE'
        emit('STOPPED: ' + code + '; NO_COMPLETION_ACTIVATION; NO_SECRET_DETAILS_PRINTED')
        return 1


if __name__ == '__main__':
    sys.exit(main())
