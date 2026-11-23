#!/usr/bin/env python3
"""Offline rollout failure tests; never import Django or contact a live service.

The real orchestration, validators, receipts, staging, backup hashes and atomic
current symlink run against temporary files. Only Git, database, HTTP, process
ownership and service adapters are synthetic. Any subprocess escape fails.
Run: python -B -m unittest discover -s ops/journey_report -p 'test_*.py' -v
"""

import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    'completed_report_rollout_under_test',
    Path(__file__).with_name('deploy_completed_report.py'),
)
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


class OfflineHost:
    """Stateful fake boundaries, with no replacement of rollout phase methods."""

    def __init__(self):
        self.events = []
        self.applied = False
        self.process_target = deploy.BASE
        self.pid = 2000
        self.fail_backup = False
        self.fail_access = False
        self.fail_report = False
        self.interrupt_after_migration = False
        self.extra_migration = False
        self.extra_plan = False
        self.bad_archive = False
        self.trip = {'status': 'completed', 'paid': True, 'driver_id': 12,
                     'driver_count': 1, 'company_count': 1,
                     'started_null': True, 'completed_null': True}
        self.base_files = {
            'requirements.txt': b'# Offline requirements fixture\n',
            'manage.py': b'# Offline source fixture; never executed\n',
            'static/offline.css': b'body { color: black; }\n',
        }
        for name in deploy.CHANGED - {'apps/trips/migrations/0009_journey_timestamps.py'}:
            self.base_files[name] = b'# Base fixture\n'
        self.app_files = dict(self.base_files)
        self.app_files.update({name: b'# Report fixture\n' for name in deploy.CHANGED})
        self.firebase = 'offline-firebase.json'
        self._seed_filesystem()

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _seed_filesystem(self):
        deploy.REPO.mkdir(parents=True)
        deploy.BASE.mkdir(parents=True)
        for name, content in self.base_files.items():
            linked_name = 'static.staged/'+name[7:] if name.startswith('static/') else name
            self.write(deploy.BASE/linked_name, content)
        self.write(deploy.VENV/'bin/python', b'offline interpreter sentinel\n')
        self.write(deploy.VENV.parent/'requirements.txt', self.base_files['requirements.txt'])
        for name in deploy.SHARED:
            target = deploy.ROOT/'shared'/name
            if name == '.env':
                self.write(target, b'OFFLINE_FIXTURE=1\n')
            else:
                target.mkdir(parents=True)
            (deploy.BASE/name).symlink_to(target)
        (deploy.BASE/'.venv').symlink_to(deploy.VENV)
        self.write(deploy.BASE/self.firebase, b'{"offline_fixture": true}\n')
        (deploy.BASE/self.firebase).chmod(0o640)
        self.write(deploy.BASE/'release.json', json.dumps({'git_sha': deploy.BASE_SHA}).encode())
        deploy.CURRENT.symlink_to(deploy.BASE)

    def git(self, *args):
        self.events.append(('git', args[0]))
        if args == ('remote', 'get-url', 'origin'):
            return b'https://github.com/mahmood1990farhat-hub/act-website-automation.git\n'
        if args == ('fetch', '--no-tags', '--no-write-fetch-head', 'origin', deploy.BASE_SHA, deploy.APP_SHA):
            return b''
        if args == ('rev-parse', deploy.APP_SHA+'^{tree}'):
            return deploy.APP_TREE.encode()
        if args == ('rev-parse', deploy.APP_SHA+':'+deploy.SUBTREE):
            return deploy.BACKEND_TREE.encode()
        if args == ('merge-base', '--is-ancestor', deploy.BASE_SHA, deploy.APP_SHA):
            return b''
        if args == ('diff', '--name-only', deploy.BASE_SHA, deploy.APP_SHA, '--', deploy.SUBTREE):
            return '\n'.join(deploy.SUBTREE+'/'+name for name in sorted(deploy.CHANGED)).encode()
        if args[:2] == ('ls-tree', '-rz'):
            trees = {deploy.BASE_SHA+':'+deploy.SUBTREE: self.base_files,
                     deploy.APP_SHA+':'+deploy.SUBTREE: self.app_files}
            return b''.join(('100644 blob '+deploy.blob_hash(content)+'\t'+name).encode()+b'\0'
                            for name, content in sorted(trees[args[2]].items()))
        if args == ('archive', '--format=tar', deploy.APP_SHA, deploy.SUBTREE):
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode='w') as tar:
                for name, content in sorted(self.app_files.items()):
                    entry = tarfile.TarInfo(deploy.SUBTREE+'/'+name)
                    entry.size = len(content)
                    tar.addfile(entry, io.BytesIO(content))
                if self.bad_archive:
                    entry = tarfile.TarInfo(deploy.SUBTREE+'/../outside-stage')
                    entry.size = 0
                    tar.addfile(entry, io.BytesIO())
            return archive.getvalue()
        raise AssertionError('Unexpected Git adapter invocation: '+repr(args))

    def db_task(self, mode, *, release=None, argument=''):
        self.events.append(('db', mode))
        if mode == 'resources':
            return {'firebase': self.firebase}
        if mode == 'inspect':
            migrations = list(deploy.TRIPS_BASE)
            if self.applied:
                migrations.append(deploy.MIGRATION)
            if self.extra_migration:
                migrations.append('0010_unapproved')
            columns = [['completed_at', 'YES', 'timestamp with time zone', None],
                       ['started_at', 'YES', 'timestamp with time zone', None]] if self.applied else []
            return {'read_only': True, 'migrations': migrations, 'columns': columns,
                    'trip37': copy.deepcopy(self.trip)}
        if mode == 'plan':
            plan = [] if self.applied else [['trips', deploy.MIGRATION, False]]
            if self.extra_plan:
                plan.append(['other_app', '0002_unapproved', False])
            return {'plan': plan}
        if mode == 'backup':
            Path(argument).write_bytes(b'offline dump sentinel; not a database archive\n')
            if self.fail_backup:
                raise deploy.Stop('Synthetic backup verification failure')
            return {'backup_verified': True}
        if mode == 'migrate':
            if self.applied:
                raise AssertionError('Migration was executed twice')
            self.applied = True
            if self.interrupt_after_migration:
                raise deploy.Stop('Synthetic interruption after migration commit')
            return {'applied': True}
        if mode == 'report':
            return {'report_schema': 0 if self.fail_report else 1,
                    'legacy_times_not_recorded': True}
        raise AssertionError('Unexpected database adapter invocation: '+mode)

    def service(self):
        return {'ActiveState': 'active', 'SubState': 'running', 'MainPID': str(self.pid),
                'WorkingDirectory': str(deploy.CURRENT), 'User': 'www-data', 'Group': 'www-data',
                'cwd': str(self.process_target)}

    def run(self, label, args, **kwargs):
        self.events.append(('run', label))
        if label == 'backup-list' and args[:2] == ['pg_restore', '--list']:
            return b'offline archive index\n'
        if label == 'backup-read' and args[:3] == ['pg_restore', '--file', '/dev/null']:
            return b''
        if label == 'service-user-read-access':
            if args[:5] != ['runuser', '-u', 'www-data', '-g', 'www-data']:
                raise AssertionError('Access check did not select the configured service identity')
            if self.fail_access:
                raise deploy.Stop('Synthetic service-user source access failure')
            # Read real staged fixture files, but do not run the supplied program.
            for name in json.loads(args[-1]):
                with (Path(args[-2])/name).open('rb'):
                    pass
            return b''
        raise AssertionError('Unexpected process adapter invocation: '+label)


class OfflineRollout(deploy.Rollout):
    def __init__(self, host, record):
        super().__init__(record)
        self.host = host

    def git(self, *args):
        return self.host.git(*args)

    def db_task(self, mode, **kwargs):
        return self.host.db_task(mode, **kwargs)

    def service(self):
        return self.host.service()

    def http(self, public=False):
        self.host.events.append(('http', public))
        return 401

    def run(self, label, args, **kwargs):
        return self.host.run(label, args, **kwargs)

    def restart(self):
        self.host.process_target = self.current_target()
        self.host.pid += 1
        self.host.events.append(('restart', 'act.service'))

    def atomic_current(self, target, expected):
        super().atomic_current(target, expected)
        self.host.events.append(('switch', target))

    def verify(self, target=None):
        # The production default is bound at import; use the temporary target.
        return super().verify(deploy.RELEASE if target is None else target)


class RolloutFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='act-rollout-offline-')
        self.addCleanup(temporary.cleanup)
        folder = Path(temporary.name)
        root = folder/'backend'
        paths = dict(ROOT=root, BASE=root/'releases/base/backend',
                     RELEASE=root/'releases/report/backend',
                     VENV=root/'releases/retained/backend/.venv', CURRENT=root/'current',
                     REPO=folder/'source-cache')
        self.enterContext(patch.multiple(deploy, **paths))
        self.record = folder/'private/record'
        self.record.parent.mkdir()
        self.host = OfflineHost()
        self.enterContext(patch.object(deploy.os, 'geteuid', return_value=0))
        self.chown = self.enterContext(patch.object(deploy.os, 'chown'))
        self.enterContext(patch.object(deploy.pwd, 'getpwnam', return_value=SimpleNamespace(pw_gid=31337)))
        self.enterContext(patch.object(deploy, 'say'))
        self.process_guard = self.enterContext(patch.object(
            deploy.subprocess, 'Popen', side_effect=AssertionError('Offline tests must never spawn a process')))
        self.enterContext(patch.object(deploy.time, 'sleep', side_effect=AssertionError('Unexpected readiness wait')))
        # Permit this suite to run as an ordinary user, without weakening any
        # receipt mode, symlink, identity, or source-content checks.
        real_stat = Path.stat

        def private_record_stat(path, *args, **kwargs):
            info = real_stat(path, *args, **kwargs)
            if path == self.record:
                fields = list(info)
                fields[4] = 0
                return os.stat_result(fields)
            return info

        self.enterContext(patch.object(Path, 'stat', private_record_stat))
        self.original_resources = self.resources()
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)

    def tearDown(self):
        self.process_guard.assert_not_called()

    def rollout(self):
        return OfflineRollout(self.host, self.record)

    def receipt(self):
        return json.loads((self.record/'receipt.json').read_bytes())

    def resources(self):
        firebase = deploy.BASE/self.host.firebase
        info = firebase.stat()
        return {'venv': (deploy.VENV/'bin/python').read_bytes(),
                'environment': (deploy.ROOT/'shared/.env').read_bytes(),
                'firebase': (firebase.read_bytes(), stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid),
                'links': {name: os.readlink(deploy.BASE/name) for name in (*deploy.SHARED, '.venv')}}

    def mutations(self, events=None):
        return [event for event in (self.host.events if events is None else events)
                if event[0] in ('switch', 'restart') or event in (('db', 'backup'), ('db', 'migrate'))]

    def assert_no_activation(self):
        self.assertEqual(deploy.CURRENT.resolve(), deploy.BASE)
        self.assertFalse(any(event[0] in ('switch', 'restart') for event in self.host.events))

    def interrupted_activation(self):
        # Build the real journal and switch, then simulate loss of the caller
        # before restart. The next execute() must reconcile from disk alone.
        first = self.rollout()
        first.preflight()
        first.stage()
        first.check_access()
        first.check_plan()
        first.ensure_backup()
        first.migrate()
        with patch.object(first, 'restart', side_effect=deploy.Stop('Synthetic process loss')):
            with self.assertRaisesRegex(deploy.Stop, 'Synthetic process loss'):
                first.activate()
        self.assertEqual(deploy.CURRENT.resolve(), deploy.RELEASE)
        self.assertEqual(self.host.process_target, deploy.BASE)
        self.assertEqual(self.receipt()['phase'], 'ACTIVATION_STARTED')
        self.assertFalse(self.receipt().get('complete', False))

    def test_source_drift_refuses_without_overwriting_or_migrating(self):
        source = deploy.BASE/'apps/trips/models/trip.py'
        source.write_bytes(b'# Existing local work must be preserved\n')
        with self.assertRaisesRegex(deploy.Stop, 'pinned source file'):
            self.rollout().execute()
        self.assertEqual(source.read_bytes(), b'# Existing local work must be preserved\n')
        self.assertFalse(deploy.RELEASE.exists())
        self.assertEqual(self.mutations(), [])
        self.assert_no_activation()

    def test_unexpected_applied_migration_refuses_before_backup(self):
        self.host.extra_migration = True
        with self.assertRaisesRegex(deploy.Stop, 'Applied trips migrations differ'):
            self.rollout().execute()
        self.assertEqual(self.mutations(), [])
        self.assert_no_activation()

    def test_unexpected_pending_migration_refuses_before_backup(self):
        self.host.extra_plan = True
        with self.assertRaisesRegex(deploy.Stop, 'Pending migration plan'):
            self.rollout().execute()
        self.assertEqual(self.mutations(), [])
        self.assert_no_activation()

    def test_backup_failure_retains_partial_evidence_and_prevents_migration(self):
        self.host.fail_backup = True
        with self.assertRaisesRegex(deploy.Stop, 'backup verification failure'):
            self.rollout().execute()
        self.assertEqual(self.mutations(), [('db', 'backup')])
        self.assertFalse(self.host.applied)
        self.assertNotIn('backup', self.receipt())
        partial = list(self.record.glob('database-before-*.dump'))
        self.assertEqual(len(partial), 1)
        self.assertGreater(partial[0].stat().st_size, 0)
        self.assert_no_activation()

    def test_source_access_failure_prevents_backup_migration_and_switch(self):
        self.host.fail_access = True
        with self.assertRaisesRegex(deploy.Stop, 'service-user source access failure'):
            self.rollout().execute()
        self.assertEqual(self.mutations(), [])
        self.assert_no_activation()

    def test_success_migrates_before_switch_with_traversable_stage_and_preserved_resources(self):
        self.rollout().execute()
        self.assertEqual(self.mutations(), [('db', 'backup'), ('db', 'migrate'),
                                           ('switch', deploy.RELEASE), ('restart', 'act.service')])
        self.assertEqual(self.receipt()['phase'], 'DEPLOYED_VERIFIED')
        self.assertTrue(self.receipt()['complete'])
        self.assertEqual(self.resources(), self.original_resources)
        self.assertEqual(self.host.trip, self.receipt()['before_trip37'])
        self.assertEqual(deploy.CURRENT.resolve(), deploy.RELEASE)
        for name in (*deploy.SHARED, '.venv'):
            self.assertEqual((deploy.RELEASE/name).resolve(), (deploy.BASE/name).resolve())
        self.assertEqual((deploy.RELEASE/self.host.firebase).read_bytes(),
                         (deploy.BASE/self.host.firebase).read_bytes())
        staged_root = Path(self.receipt()['staging_attempts'][-1])
        dirs = [deploy.RELEASE.parent, deploy.RELEASE]
        dirs += [path for path in deploy.RELEASE.rglob('*') if path.is_dir() and not path.is_symlink()]
        ownership = {(Path(call.args[0]), call.args[1], call.args[2]) for call in self.chown.call_args_list}
        for directory in dirs:
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o750, str(directory))
            before_rename = staged_root/directory.relative_to(deploy.RELEASE.parent)
            self.assertIn((before_rename, 0, 31337), ownership)
        self.assertEqual(stat.S_IMODE(self.record.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.record/'receipt.json').stat().st_mode), 0o600)

    def test_postcheck_failure_restores_pointer_but_retains_schema_backup_and_resources(self):
        self.host.fail_report = True
        with self.assertRaisesRegex(deploy.Stop, 'Read-only report verification failed'):
            self.rollout().execute()
        self.assertEqual(self.mutations(), [('db', 'backup'), ('db', 'migrate'),
                                           ('switch', deploy.RELEASE), ('restart', 'act.service'),
                                           ('switch', deploy.BASE), ('restart', 'act.service')])
        self.assertEqual(deploy.CURRENT.resolve(), deploy.BASE)
        self.assertEqual(self.host.process_target, deploy.BASE)
        self.assertTrue(self.host.applied)
        self.assertTrue(deploy.validate_schema_snapshot(self.host.db_task('inspect')))
        receipt = self.receipt()
        self.assertEqual(receipt['phase'], 'PREVIOUS_BACKEND_RESTORED_COLUMNS_RETAINED')
        self.assertFalse(receipt.get('complete', False))
        self.assertEqual(deploy.file_sha256(Path(receipt['backup']['path'])), receipt['backup']['sha256'])
        self.assertEqual(self.resources(), self.original_resources)
        for name in (*deploy.SHARED, '.venv'):
            self.assertEqual((deploy.RELEASE/name).resolve(), (deploy.BASE/name).resolve())
        self.assertEqual((deploy.RELEASE/self.host.firebase).read_bytes(),
                         (deploy.BASE/self.host.firebase).read_bytes())

    def test_retry_after_rollback_reuses_backup_and_does_not_repeat_migration_or_stage(self):
        self.host.fail_report = True
        with self.assertRaises(deploy.Stop):
            self.rollout().execute()
        before = self.receipt()
        offset = len(self.host.events)
        self.host.fail_report = False
        self.rollout().execute()
        retry_events = self.host.events[offset:]
        self.assertEqual(self.mutations(retry_events), [('switch', deploy.RELEASE), ('restart', 'act.service')])
        self.assertNotIn(('git', 'archive'), retry_events)
        self.assertEqual(self.receipt()['backup'], before['backup'])
        self.assertEqual(self.receipt()['staging_attempts'], before['staging_attempts'])
        self.assertTrue(self.receipt()['complete'])

    def test_auxiliary_failure_log_error_cannot_prevent_postactivation_recovery(self):
        self.host.fail_report = True
        real_write_bytes = Path.write_bytes
        failed_logs = []

        def unavailable_failure_log(path, *args, **kwargs):
            if path.parent == self.record and path.name.endswith('-failure.log'):
                failed_logs.append(path)
                raise OSError('Synthetic auxiliary log write failure')
            return real_write_bytes(path, *args, **kwargs)

        with patch.object(Path, 'write_bytes', unavailable_failure_log):
            with self.assertRaisesRegex(deploy.Stop, 'Read-only report verification failed'):
                self.rollout().execute()
        self.assertEqual(len(failed_logs), 1)
        self.assertEqual(self.mutations(), [('db', 'backup'), ('db', 'migrate'),
                                           ('switch', deploy.RELEASE), ('restart', 'act.service'),
                                           ('switch', deploy.BASE), ('restart', 'act.service')])
        self.assertEqual(deploy.CURRENT.resolve(), deploy.BASE)
        self.assertEqual(self.host.process_target, deploy.BASE)
        self.assertTrue(self.host.applied)
        self.assertEqual(self.receipt()['phase'], 'PREVIOUS_BACKEND_RESTORED_COLUMNS_RETAINED')
        self.assertEqual(self.resources(), self.original_resources)

    def test_command_log_failure_preserves_success_output_and_nonzero_exit_failure(self):
        self.record.mkdir(mode=0o700)
        real_write_bytes = Path.write_bytes
        failed_logs = []

        def unavailable_command_log(path, data):
            if path.parent == self.record and path.suffix == '.log':
                failed_logs.append(path)
                raise OSError('Synthetic full diagnostic storage')
            return real_write_bytes(path, data)

        class OfflineProcess:
            def __init__(self, returncode):
                self.returncode = returncode

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def communicate(self, timeout=None):
                return b'offline command result\n', b'offline diagnostics\n'

        runner = deploy.Rollout(self.record)
        with patch.object(Path, 'write_bytes', unavailable_command_log):
            with patch.object(deploy.subprocess, 'Popen',
                              side_effect=[OfflineProcess(0), OfflineProcess(17)]) as fake_popen:
                self.assertEqual(runner.run('fixture-command', ['offline-command']),
                                 b'offline command result\n')
                with self.assertRaisesRegex(deploy.Stop, 'fixture-command failed'):
                    runner.run('fixture-command', ['offline-command'])
        self.assertEqual(fake_popen.call_count, 2)
        self.assertEqual(len(failed_logs), 2)
        # The signal handler raises Stop: ordinary diagnostics must not swallow
        # an operator interruption while suppressing only storage errors.
        with patch.object(Path, 'write_bytes', side_effect=deploy.Stop('Synthetic operator interruption')):
            with patch.object(deploy.subprocess, 'Popen', return_value=OfflineProcess(0)):
                with self.assertRaisesRegex(deploy.Stop, 'Synthetic operator interruption'):
                    runner.run('fixture-command', ['offline-command'])

    def test_interrupted_migration_commit_is_detected_and_not_repeated(self):
        self.host.interrupt_after_migration = True
        with self.assertRaisesRegex(deploy.Stop, 'interruption after migration commit'):
            self.rollout().execute()
        self.assertTrue(self.host.applied)
        self.assert_no_activation()
        offset = len(self.host.events)
        self.host.interrupt_after_migration = False
        self.rollout().execute()
        self.assertEqual(self.mutations(self.host.events[offset:]),
                         [('switch', deploy.RELEASE), ('restart', 'act.service')])
        self.assertEqual(self.host.events.count(('db', 'migrate')), 1)

    def test_corrupt_verified_backup_blocks_retry_before_activation(self):
        self.host.interrupt_after_migration = True
        with self.assertRaises(deploy.Stop):
            self.rollout().execute()
        backup = Path(self.receipt()['backup']['path'])
        backup.write_bytes(b'changed offline backup')
        offset = len(self.host.events)
        self.host.interrupt_after_migration = False
        with self.assertRaisesRegex(deploy.Stop, 'Verified backup is absent, changed or incomplete'):
            self.rollout().execute()
        self.assertEqual(self.mutations(self.host.events[offset:]), [])
        self.assert_no_activation()
        self.assertTrue(self.host.applied)

    def test_interrupted_activation_early_check_failure_restores_previous_pointer(self):
        self.interrupted_activation()
        offset = len(self.host.events)
        self.host.fail_access = True
        with self.assertRaisesRegex(deploy.Stop, 'service-user source access failure'):
            self.rollout().execute()
        self.assertEqual(self.mutations(self.host.events[offset:]),
                         [('switch', deploy.BASE), ('restart', 'act.service')])
        self.assertEqual(deploy.CURRENT.resolve(), deploy.BASE)
        self.assertEqual(self.host.process_target, deploy.BASE)
        self.assertTrue(self.host.applied)
        self.assertEqual(self.receipt()['phase'], 'PREVIOUS_BACKEND_RESTORED_COLUMNS_RETAINED')
        self.assertEqual(self.resources(), self.original_resources)

    def test_interrupted_activation_restart_then_failed_postcheck_restores_previous_pointer(self):
        self.interrupted_activation()
        offset = len(self.host.events)
        self.host.fail_report = True
        with self.assertRaisesRegex(deploy.Stop, 'Read-only report verification failed'):
            self.rollout().execute()
        self.assertEqual(self.mutations(self.host.events[offset:]),
                         [('restart', 'act.service'), ('switch', deploy.BASE), ('restart', 'act.service')])
        self.assertEqual(deploy.CURRENT.resolve(), deploy.BASE)
        self.assertEqual(self.host.process_target, deploy.BASE)
        self.assertTrue(self.host.applied)
        self.assertEqual(self.receipt()['phase'], 'PREVIOUS_BACKEND_RESTORED_COLUMNS_RETAINED')
        self.assertEqual(self.resources(), self.original_resources)

    def test_accepted_retry_neither_redeploys_nor_rewrites_acceptance_receipt(self):
        self.rollout().execute()
        accepted = (self.record/'receipt.json').read_bytes()
        offset = len(self.host.events)
        self.rollout().execute()
        self.assertEqual(self.mutations(self.host.events[offset:]), [])
        self.assertNotIn(('git', 'archive'), self.host.events[offset:])
        self.assertEqual((self.record/'receipt.json').read_bytes(), accepted)

    def test_accepted_retry_postcheck_failure_does_not_rollback_or_downgrade_receipt(self):
        self.rollout().execute()
        accepted = (self.record/'receipt.json').read_bytes()
        offset = len(self.host.events)
        self.host.fail_report = True
        with self.assertRaisesRegex(deploy.Stop, 'Read-only report verification failed'):
            self.rollout().execute()
        self.assertEqual(self.mutations(self.host.events[offset:]), [])
        self.assertEqual(deploy.CURRENT.resolve(), deploy.RELEASE)
        self.assertEqual(self.host.process_target, deploy.RELEASE)
        self.assertEqual((self.record/'receipt.json').read_bytes(), accepted)

    def test_unknown_candidate_release_is_never_overwritten_even_with_started_receipt(self):
        self.rollout().preflight()
        deploy.RELEASE.mkdir(parents=True)
        sentinel = deploy.RELEASE/'unknown-partial-work.txt'
        sentinel.write_bytes(b'keep existing work\n')
        (deploy.RELEASE/'release.json').write_text('{"git_sha": "unknown"}')
        with self.assertRaisesRegex(deploy.Stop, 'Unowned candidate'):
            self.rollout().execute()
        self.assertEqual(sentinel.read_bytes(), b'keep existing work\n')
        self.assertEqual(self.mutations(), [])
        self.assertNotIn(('git', 'archive'), self.host.events)
        self.assert_no_activation()

    def test_interrupted_stage_is_preserved_and_retry_uses_a_new_private_stage(self):
        self.host.bad_archive = True
        with self.assertRaisesRegex(deploy.Stop, 'Unsafe source archive member'):
            self.rollout().execute()
        abandoned = Path(self.receipt()['staging_attempts'][0])
        source = abandoned/'backend/manage.py'
        saved = source.read_bytes()
        self.assertFalse(deploy.RELEASE.exists())
        self.assertEqual(self.mutations(), [])
        self.host.bad_archive = False
        self.rollout().execute()
        self.assertEqual(source.read_bytes(), saved)
        self.assertEqual(len(self.receipt()['staging_attempts']), 2)
        self.assertTrue(self.receipt()['complete'])


if __name__ == '__main__':
    unittest.main()
