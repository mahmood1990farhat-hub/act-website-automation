"""Focused activation guards and recovery checks; all host surfaces are fake.

Tests operate on temporary files or an isolated JavaScript VM. They never call
the VPS, GitHub, PM2, systemd, Nginx, public HTTP or the ACT application.
"""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).with_name('activate_existing_tracking.py')
SPEC = importlib.util.spec_from_file_location('activation_under_test', SOURCE)
act = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = act
SPEC.loader.exec_module(act)


def staged_plan(record):
    """Synthetic data in the real staged-plan schema; no file is read here."""
    tag = record.name.removeprefix('tracking-stage-')
    backend = act.BACK_ROOT / 'releases' / f'20261106-tracking-{act.BACKEND_SHA[:7]}-{tag}' / 'backend'
    frontend = act.FRONT_ROOT / 'releases' / f'20261106-tracking-{act.FRONTEND_SHA[:7]}-{tag}'
    return {
        'state': 'STAGED_NOT_ACTIVE', 'backend_sha': act.BACKEND_SHA,
        'frontend_sha': act.FRONTEND_SHA, 'backend_release': str(backend),
        'frontend_release': str(frontend),
        'public_assets': str(act.FRONT_ROOT / f'act-static-tracking-{act.FRONTEND_SHA[:7]}-{tag}'),
        'live_site': str(act.SITE), 'live_site_resolved': '/etc/nginx/sites-available/act-test',
        'prior_upstream': '127.0.0.1:3002', 'candidate_upstream': '127.0.0.1:3003',
        'candidate_pm2_name': 'act-tracking-' + act.FRONTEND_SHA[:7],
        'private_public_environment_file': str(record / 'frontend-public-environment.json'),
        'pm2_launch': {'cwd': str(frontend), 'script': str(frontend / 'node_modules/next/dist/bin/next'),
                       'interpreter': str(act.NODE), 'args': act.ARGS, 'env': {'NODE_ENV': 'production'}},
        'api_origin': act.ORIGIN, 'stripe_public_mode': 'test', 'maps_key_present': True,
        'nginx_validation_passed': True, 'candidate_listener_started': False,
        'backend_changed_application_files': ['apps/trips/consumers.py'],
        'frontend_changed_application_files': sorted(act.FRONT_FILES),
        'backend': {'git_sha': act.BACKEND_SHA, 'state': 'STAGED_NOT_ACTIVE',
                    'consumer_sha256': act.CONSUMER_HASH, 'venv_provider': str(act.VENV)},
        **{key: str(number) * 64 for number, key in enumerate((
            'original_sha256', 'candidate_sha256', 'rollback_sha256',
            'asset_manifest_sha256', 'frontend_lock_sha256'))},
        'frontend_build_id': 'fixture-build-id',
    }


class PlanAndPrivacyChecks(unittest.TestCase):
    def test_plan_accepts_only_the_staged_pair_and_exact_new_loopback_launch(self):
        record = act.BACKUP_ROOT / 'tracking-stage-test0001'
        plan = staged_plan(record)
        act.validate_plan(record, plan)
        changes = (
            ('state', 'ACTIVATED'), ('backend_sha', act.BACK_BASE),
            ('frontend_sha', act.FRONT_BASE), ('candidate_upstream', '0.0.0.0:3003'),
            ('prior_upstream', '127.0.0.1:3001'), ('candidate_pm2_name', 'act'),
            ('backend_release', str(act.BACK_OLD)), ('candidate_listener_started', True),
            ('private_public_environment_file', '/tmp/untrusted-public-environment.json'),
        )
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(act.Stop):
                act.validate_plan(record, plan | {key: value})
        changed = copy.deepcopy(plan)
        changed['pm2_launch']['args'] = ['start', '--hostname', '0.0.0.0', '--port', '3003']
        with self.assertRaises(act.Stop):
            act.validate_plan(record, changed)
        changed = copy.deepcopy(plan)
        changed['backend_changed_application_files'].append('apps/payments/views/views.py')
        with self.assertRaises(act.Stop):
            act.validate_plan(record, changed)

    def test_public_environment_rejects_private_fields_and_errors_do_not_echo_values(self):
        values = {'NEXT_PUBLIC_API_BASE_URL': act.ORIGIN,
                  'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY': 'pk_test_' + 'x' * 24,
                  'NEXT_PUBLIC_GOOGLE_MAPS_API_KEY': 'AIza' + 'y' * 35}
        act.public_environment(values)
        sentinel = 'SENSITIVE_TEST_ONLY_NEVER_ECHO'
        with self.assertRaises(act.Stop) as caught:
            act.public_environment(values | {'PRIVATE_CREDENTIAL': sentinel})
        self.assertNotIn(sentinel, str(caught.exception))
        with self.assertRaises(act.Stop):
            act.public_environment(values | {'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY': 'pk_live_' + 'x' * 24})

    def test_saved_pm2_environment_drift_is_refused_without_echoing_the_environment(self):
        settings = {key: None for key in act.LAUNCH_FIELDS}
        settings['env'] = {'NODE_ENV': 'production', 'PRIVATE_SENTINEL': 'test-private-value'}
        saved = {'name': 'act'} | copy.deepcopy(settings)
        live = {'name': 'act', 'pm2_env': copy.deepcopy(settings)}
        act.saved_matches_live(saved, live)
        saved['env'].pop('PRIVATE_SENTINEL')
        with self.assertRaises(act.Stop) as caught:
            act.saved_matches_live(saved, live)
        self.assertNotIn('test-private-value', str(caught.exception))

    def test_disconnected_stdout_is_nonfatal(self):
        for failure in (BrokenPipeError('test terminal closed'), OSError('test terminal unavailable')):
            with self.subTest(failure=type(failure).__name__), patch('builtins.print', side_effect=failure):
                act.say('sanitized progress')


class AtomicMutationChecks(unittest.TestCase):
    def test_site_replace_preserves_enabled_link_owner_mode_and_extended_attributes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = root / 'available-site'
            site.write_bytes(b'original routing\n')
            site.chmod(0o640)
            os.setxattr(site, 'user.act-test', b'retained metadata')
            enabled = root / 'enabled-site'
            enabled.symlink_to(site)
            old = site.stat()
            old_link = os.readlink(enabled)
            act.atomic_site(site, b'candidate routing\n', act.sha(site.read_bytes()))
            after = site.stat()
            self.assertEqual(enabled.read_bytes(), b'candidate routing\n')
            self.assertTrue(enabled.is_symlink())
            self.assertEqual(os.readlink(enabled), old_link)
            self.assertEqual((after.st_uid, after.st_gid), (old.st_uid, old.st_gid))
            self.assertEqual(stat.S_IMODE(after.st_mode), 0o640)
            self.assertEqual(os.getxattr(site, 'user.act-test'), b'retained metadata')

    def test_site_concurrent_edit_is_not_overwritten_and_temporary_file_is_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = root / 'site'
            site.write_bytes(b'original')
            expected = act.sha(site.read_bytes())
            make_temp = act.tempfile.mkstemp

            def competing_edit(*args, **kwargs):
                result = make_temp(*args, **kwargs)
                site.write_bytes(b'concurrent operator edit')
                return result

            with patch.object(act.tempfile, 'mkstemp', side_effect=competing_edit):
                with self.assertRaises(act.Stop):
                    act.atomic_site(site, b'candidate', expected)
            self.assertEqual(site.read_bytes(), b'concurrent operator edit')
            self.assertEqual(list(root.iterdir()), [site])

    def test_site_symlink_and_hardlink_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.write_bytes(b'keep')
            linked = root / 'linked'
            linked.symlink_to(source)
            with self.assertRaises(act.Stop):
                act.atomic_site(linked, b'new', act.sha(b'keep'))
            linked.unlink()
            os.link(source, linked)
            with self.assertRaises(act.Stop):
                act.atomic_site(source, b'new', act.sha(b'keep'))
            self.assertEqual(source.read_bytes(), b'keep')
            self.assertEqual(linked.read_bytes(), b'keep')

    def test_backend_current_switch_and_restore_require_exact_preimages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old, candidate, concurrent = (root / name for name in ('old', 'candidate', 'concurrent'))
            for path in (old, candidate, concurrent):
                path.mkdir()
            current = root / 'current'
            current.symlink_to(old)
            with patch.object(act, 'CURRENT', current):
                act.atomic_current(candidate, old)
                self.assertEqual(current.resolve(), candidate)
                act.atomic_current(old, candidate)
                self.assertEqual(current.resolve(), old)
                current.unlink()
                current.symlink_to(concurrent)
                with self.assertRaises(act.Stop):
                    act.atomic_current(old, candidate)
                self.assertEqual(current.resolve(), concurrent)


class FakeWebSocket:
    """Byte-stream fixture for the actual RFC6455 refusal client."""
    def __init__(self, frames, valid_upgrade=True):
        self.frames = frames
        self.valid_upgrade = valid_upgrade
        self.incoming = bytearray()
        self.sent = []
        self.auth_message = None
        self.address = None
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        self.address = address

    def sendall(self, data):
        self.sent.append(data)
        if len(self.sent) == 1:
            fields = dict(line.split(':', 1) for line in data.decode().split('\r\n')[1:] if ':' in line)
            key = fields['Sec-WebSocket-Key'].strip()
            accept = act.base64.b64encode(act.hashlib.sha1(
                (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            if not self.valid_upgrade:
                accept = 'invalid-upgrade'
            self.incoming.extend(('HTTP/1.1 101 Switching Protocols\r\n'
                                  'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                                  f'Sec-WebSocket-Accept: {accept}\r\n\r\n').encode())
        else:
            assert data[0] == 0x81 and data[1] & 0x80
            length = data[1] & 0x7f
            assert length < 126 and len(data) == 6 + length
            mask, body = data[2:6], data[6:]
            self.auth_message = json.loads(bytes(value ^ mask[i % 4] for i, value in enumerate(body)))
            self.incoming.extend(b''.join(self.frames))

    def recv(self, count):
        # Deliberately fragmented reads exercise recv_exact rather than returning
        # complete frames in one convenient operation.
        size = min(count, 3, len(self.incoming))
        result = bytes(self.incoming[:size])
        del self.incoming[:size]
        return result


def ws_frame(opcode, payload):
    assert len(payload) < 126
    return bytes([0x80 | opcode, len(payload)]) + payload


class AnonymousTransportChecks(unittest.TestCase):
    def test_probe_sends_only_tokenless_viewer_auth_and_requires_error_then_4403(self):
        connection = FakeWebSocket([
            ws_frame(1, b'{"type":"auth_error"}'),
            ws_frame(8, act.struct.pack('!H', 4403)),
        ])
        output = io.StringIO()
        with patch.object(act.socket, 'socket', return_value=connection), redirect_stdout(output), redirect_stderr(output):
            act.anonymous_refusal()
        self.assertEqual(connection.address, '/run/act.sock')
        self.assertEqual(connection.timeout, 5)
        self.assertTrue(connection.sent[0].startswith(b'GET /ws/trips/0/tracking/ HTTP/1.1\r\n'))
        self.assertEqual(connection.auth_message, {'type': 'viewer_auth'})
        self.assertEqual(len(connection.sent), 2)
        self.assertEqual(output.getvalue(), '')

    def test_probe_refuses_a_location_success_bad_upgrade_or_wrong_close_without_echoing_payload(self):
        sensitive_payload = b'{"type":"location","test_private_marker":"DO_NOT_ECHO","lat":51.4,"lng":-0.4}'
        cases = (
            (True, [ws_frame(1, sensitive_payload), ws_frame(8, act.struct.pack('!H', 4403))]),
            (True, [ws_frame(1, b'{"type":"auth_ok"}'), ws_frame(8, act.struct.pack('!H', 4403))]),
            (True, [ws_frame(1, b'{"type":"auth_error"}'), ws_frame(8, act.struct.pack('!H', 1000))]),
            (False, [ws_frame(1, b'{"type":"auth_error"}'), ws_frame(8, act.struct.pack('!H', 4403))]),
        )
        for number, (valid_upgrade, frames) in enumerate(cases):
            connection = FakeWebSocket(frames, valid_upgrade)
            output = io.StringIO()
            with self.subTest(case=number), patch.object(act.socket, 'socket', return_value=connection), redirect_stdout(output), redirect_stderr(output):
                with self.assertRaises(act.Stop) as caught:
                    act.anonymous_refusal()
                self.assertNotIn('DO_NOT_ECHO', str(caught.exception))
                self.assertNotIn('DO_NOT_ECHO', output.getvalue())
                if not valid_upgrade:
                    self.assertEqual(len(connection.sent), 1)


class LocalHost:
    """A temporary filesystem and fake service surfaces for actual transactions."""
    def __init__(self, test):
        self.test = test
        temporary = tempfile.TemporaryDirectory()
        test.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        stack = ExitStack()
        test.addCleanup(stack.close)
        self.back_root = self.root / 'backend'
        self.front_root = self.root / 'frontend'
        self.back_old = self.back_root / 'releases/old/backend'
        self.front_old = self.front_root / 'releases/old'
        self.current = self.back_root / 'current'
        self.backup_root = self.root / 'backup'
        self.record = self.backup_root / 'tracking-stage-test0001'
        self.site = self.root / 'nginx/sites-available/act'
        self.enabled = self.root / 'nginx/sites-enabled/airportandcitytransfer'
        self.master = self.root / 'nginx/nginx.conf'
        self.pm2_home = self.root / 'pm2'
        self.dump = self.pm2_home / 'dump.pm2'
        self.venv = self.back_root / 'releases/provider/backend/.venv'
        replacements = {
            'BACK_ROOT': self.back_root, 'BACK_OLD': self.back_old,
            'FRONT_ROOT': self.front_root, 'FRONT_OLD': self.front_old,
            'CURRENT': self.current, 'BACKUP_ROOT': self.backup_root,
            'SITE': self.enabled, 'MASTER': self.master, 'VENV': self.venv,
            'PM2_HOME': self.pm2_home, 'DUMP': self.dump,
            'OLD_ASSETS': self.front_root / 'old-assets',
        }
        for name, value in replacements.items():
            stack.enter_context(patch.object(act, name, value))
        for directory in (self.back_old, self.front_old, self.record, self.site.parent,
                          self.enabled.parent, self.pm2_home, self.back_root / 'shared'):
            directory.mkdir(parents=True, exist_ok=True)
        self.record.chmod(0o700)
        self.current.symlink_to(self.back_old)
        self.plan = staged_plan(self.record)
        self.backend = Path(self.plan['backend_release'])
        self.frontend = Path(self.plan['frontend_release'])
        self.assets = Path(self.plan['public_assets'])
        for directory in (self.backend, self.frontend, self.assets):
            directory.mkdir(parents=True)
        shared = self.back_root / 'shared/.env'
        shared.write_bytes(b'fixture-only-private-environment\n')
        self.plan['backend']['shared_environment_sha256'] = act.sha(shared.read_bytes())
        self.plan['backend']['requirements_sha256'] = 'a' * 64
        (self.back_old / 'release.json').write_bytes(act.json_bytes({'git_sha': act.BACK_BASE}))
        (self.backend / 'release.json').write_bytes(act.json_bytes(self.plan['backend']))
        consumer = self.backend / 'apps/trips/consumers.py'
        consumer.parent.mkdir(parents=True)
        consumer.write_text('intentionally not the pinned consumer\n')
        self.original = (
            'location / {\n proxy_pass http://127.0.0.1:3002;\n}\n'
            'location /api/places {\n proxy_pass http://127.0.0.1:3002;\n}\n'
            'location /api/place-details {\n proxy_pass http://127.0.0.1:3002;\n}\n'
            f'location /_next/static/ {{\n alias {act.OLD_ASSETS}/;\n}}\n'
            'location /ws/ { proxy_pass http://unix:/run/act.sock; }\n'
        ).encode()
        self.candidate, self.rollback = act.route_pair(self.original, self.assets)
        self.site.write_bytes(self.original)
        self.enabled.symlink_to(self.site)
        self.master.write_text('pid /run/nginx.pid;\nhttp {\n include /etc/nginx/sites-enabled/*;\n}\n')
        self.plan['live_site_resolved'] = str(self.site)
        for name, data in (('original', self.original), ('candidate', self.candidate), ('rollback', self.rollback)):
            self.plan[name + '_sha256'] = act.sha(data)
        self.write_plan()
        self.rows = []
        for index, name in enumerate(act.RETAINED):
            settings = {
                'name': name, 'pm_cwd': str(self.front_old),
                'pm_exec_path': str(self.front_old / 'node_modules/next/dist/bin/next'),
                'exec_interpreter': str(act.NODE),
                'args': ['start', '--hostname', '127.0.0.1', '--port', str(3001 + index)],
                'exec_mode': 'fork_mode', 'env': {'NODE_ENV': 'production', 'KEEP_PRIVATE': 'fixture-only'},
                **act.POLICY, 'status': 'online', 'restart_time': 0, 'pm_uptime': 1000 + index,
            }
            self.rows.append({'name': name, 'pm_id': index, 'pid': 10 + index, 'pm2_env': settings})
        self.saved = [copy.deepcopy(row['pm2_env']) for row in self.rows]
        # Deliberately noncanonical whitespace proves exact-byte recovery.
        self.dump_before = json.dumps(self.saved, indent=3).encode() + b'\n\n'
        self.dump.write_bytes(self.dump_before)
        self.dump.chmod(0o600)

    def write_plan(self):
        path = self.record / 'plan.json'
        path.write_bytes(act.json_bytes(self.plan))
        path.chmod(0o600)

    def operation(self):
        op = act.Activation(self.record)
        op.work = self.record / 'activation-fixture'
        op.work.mkdir(mode=0o700)
        op.plan = self.plan
        op.backend, op.frontend, op.assets = self.backend, self.frontend, self.assets
        op.site, op.master = self.site, self.master.read_bytes()
        op.entries = sorted(self.enabled.parent.iterdir())
        op.original, op.candidate, op.rollback = self.original, self.candidate, self.rollback
        op.old_hash, op.new_hash, op.rollback_hash = map(act.sha, (self.original, self.candidate, self.rollback))
        op.dump_before, op.saved_before = self.dump_before, copy.deepcopy(self.saved)
        op.retained = [act.pm2_identity(row) for row in self.rows]
        op.pm2_rows = Mock(side_effect=lambda: copy.deepcopy(self.rows))
        op.require_retained = Mock()
        op.daemon_pid = 123
        op.name = self.plan['candidate_pm2_name']
        op.public = {'NEXT_PUBLIC_API_BASE_URL': act.ORIGIN,
                     'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY': 'pk_test_' + 'x' * 24,
                     'NEXT_PUBLIC_GOOGLE_MAPS_API_KEY': 'AIza' + 'y' * 35}
        op.backend_before = {'ActiveState': 'active', 'MainPID': '90', 'WorkingDirectory': str(self.current)}
        op.backend_after = op.backend_before | {'MainPID': '91'}
        op.unchanged_units = {name: {'ActiveState': 'active', 'MainPID': str(100 + index), 'WorkingDirectory': '/unchanged'}
                              for index, name in enumerate(act.UNCHANGED_UNITS)}

        def unit(name):
            if name != 'act.service':
                return op.unchanged_units[name]
            return op.backend_after if self.current.resolve() == self.backend else op.backend_before

        op.unit = Mock(side_effect=unit)
        op.command = Mock(return_value=b'')
        op.check_backend = Mock()
        return op

    def point_current(self, target):
        self.current.unlink()
        self.current.symlink_to(target)


class PreflightAndCommandChecks(unittest.TestCase):
    def test_current_drift_and_modified_consumer_stop_before_any_service_or_process_call(self):
        for scenario in ('current', 'consumer'):
            with self.subTest(scenario=scenario):
                host = LocalHost(self)
                if scenario == 'current':
                    unexpected = host.root / 'concurrent-backend'
                    unexpected.mkdir()
                    host.point_current(unexpected)
                op = act.Activation(host.record)
                with patch.object(op, 'command') as command, patch.object(act, 'say'):
                    with self.assertRaises(act.Stop):
                        op.preflight()
                    command.assert_not_called()
                self.assertFalse(op.backend_attempted)
                self.assertEqual(host.site.read_bytes(), host.original)
                self.assertEqual(host.dump.read_bytes(), host.dump_before)

    def test_existing_activation_journal_prevents_a_repeat_before_any_command(self):
        host = LocalHost(self)
        journal = host.record / 'activation-prior'
        journal.mkdir()
        (journal / 'STARTED.json').write_text('{"state":"STARTED"}')
        op = act.Activation(host.record)
        with patch.object(op, 'command') as command:
            with self.assertRaises(act.Stop):
                op.preflight()
            command.assert_not_called()
        self.assertIsNone(op.work)
        self.assertEqual(list(host.record.glob('activation-*')), [journal])

    def test_command_failure_keeps_payload_private_and_reports_only_sanitized_reason(self):
        host = LocalHost(self)
        op = host.operation()
        # Use the real command wrapper, not this fixture's fake service surface.
        del op.command
        marker = b'TEST_PRIVATE_TOKEN_SHOULD_NOT_REACH_TERMINAL'
        result = subprocess.CompletedProcess(['fake-command'], 1, marker, marker)
        output = io.StringIO()
        with patch.object(act, 'run', return_value=result), redirect_stdout(output), redirect_stderr(output):
            with self.assertRaises(act.Stop) as caught:
                op.command('fixture-command', ['fake-command'])
        self.assertNotIn(marker.decode(), str(caught.exception))
        self.assertEqual(output.getvalue(), '')
        logs = list(op.work.glob('*.log'))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].read_bytes(), marker + marker)
        self.assertEqual(stat.S_IMODE(logs[0].stat().st_mode), 0o600)


class TransactionRecoveryChecks(unittest.TestCase):
    def test_failed_new_backend_restores_previous_pointer_restarts_only_act_and_blocks_gps(self):
        host = LocalHost(self)
        op = host.operation()

        def readiness(target):
            if target == host.backend:
                raise act.Stop('Fixture backend readiness failure')

        op.check_backend.side_effect = readiness
        with patch.object(act, 'say'):
            with self.assertRaises(act.Stop):
                op.activate()
            op.recover()
        self.assertEqual(host.current.resolve(), host.back_old)
        self.assertFalse(op.backend_healthy)
        self.assertFalse(op.frontend_attempted)
        self.assertEqual([call.args[0] for call in op.command.call_args_list], ['backend-restart', 'backend-restore-restart'])
        for call in op.command.call_args_list:
            self.assertEqual(call.args[1], ['/usr/bin/systemctl', 'restart', 'act.service'])
        self.assertEqual([call.args[0] for call in op.check_backend.call_args_list], [host.backend, host.back_old])
        receipt = json.loads((op.work / 'BACKEND_ROLLED_BACK_GPS_BLOCKED.json').read_bytes())
        self.assertFalse(receipt['public_activation_complete'])
        self.assertFalse(receipt['real_phone_gps_started_by_helper'])

    def test_frontend_start_failure_preserves_authenticated_backend_and_exact_old_dump(self):
        host = LocalHost(self)
        op = host.operation()

        def command(label, *args, **kwargs):
            if label == 'pm2-start-candidate':
                # Simulate daemon prepare succeeding but its acknowledgement
                # failing. Recovery owns this candidate through its nonce.
                payload = json.loads(kwargs['input'])
                config = payload['config']
                self.assertEqual(config['args'], ['start', '--hostname', '127.0.0.1', '--port', '3003'])
                self.assertTrue(all(config['env'][key] == value for key, value in op.public.items()))
                self.assertNotIn('KEEP_PRIVATE', config['env'])
                host.rows.append({'name': op.name, 'pm_id': 2, 'pid': 200,
                                  'pm2_env': {'env': config['env']}})
                raise act.Stop('Fixture PM2 candidate failure')
            if label == 'pm2-remove-only-new-candidate':
                payload = json.loads(kwargs['input'])
                self.assertEqual(payload['activation_nonce'], host.rows[-1]['pm2_env']['env']['ACT_TRACKING_ACTIVATION'])
                self.assertFalse(payload['allow_absent'])
                host.rows.pop()
            return b''

        op.command.side_effect = command
        with patch.object(act, 'say'):
            with self.assertRaises(act.Stop):
                op.activate()
            op.recover()
        self.assertTrue(op.backend_healthy)
        self.assertTrue(op.frontend_attempted)
        self.assertEqual(host.current.resolve(), host.backend)
        self.assertEqual(host.site.read_bytes(), host.original)
        self.assertEqual(host.dump.read_bytes(), host.dump_before)
        self.assertEqual([row['name'] for row in host.rows], list(act.RETAINED))
        labels = [call.args[0] for call in op.command.call_args_list]
        self.assertEqual(labels, ['backend-restart', 'pm2-start-candidate', 'pm2-remove-only-new-candidate'])
        self.assertNotIn('backend-restore-restart', labels)
        self.assertTrue((op.work / 'FRONTEND_ROLLED_BACK_AUTHENTICATED_BACKEND_RETAINED.json').is_file())

    def test_public_failure_restores_3002_with_combined_assets_and_keeps_secure_backend(self):
        host = LocalHost(self)
        op = host.operation()
        host.point_current(host.backend)
        host.site.write_bytes(host.candidate)
        op.backend_attempted = op.backend_healthy = op.frontend_attempted = True
        op.route_attempted = op.reload_attempted = op.dump_attempted = True
        op.dump_new = act.json_bytes([*host.saved, {'name': op.name}])
        op.dump_new_hash = act.sha(op.dump_new)
        host.dump.write_bytes(op.dump_new)
        op.nginx, op.reload, op.check_frontend_routes, op.remove_new_frontend = Mock(), Mock(), Mock(), Mock()
        with patch.object(act, 'say'):
            op.recover()
        self.assertEqual(host.site.read_bytes(), host.rollback)
        self.assertEqual(host.site.read_bytes().count(b'127.0.0.1:3002'), 3)
        self.assertIn(str(host.assets).encode(), host.site.read_bytes())
        self.assertIn(b'/run/act.sock', host.site.read_bytes())
        self.assertEqual(host.current.resolve(), host.backend)
        self.assertEqual(host.dump.read_bytes(), host.dump_before)
        op.reload.assert_called_once()
        op.check_frontend_routes.assert_called_once_with(False)
        op.remove_new_frontend.assert_called_once()
        op.check_backend.assert_called_once_with(host.backend)

    def test_concurrent_routing_change_withholds_cleanup_before_or_after_our_route_step(self):
        for route_attempted in (False, True):
            with self.subTest(route_attempted=route_attempted):
                host = LocalHost(self)
                op = host.operation()
                host.point_current(host.backend)
                op.backend_attempted = op.backend_healthy = op.frontend_attempted = True
                op.route_attempted = route_attempted
                op.reload_attempted = route_attempted
                host.site.write_bytes(b'concurrent operator routing')
                op.remove_new_frontend = Mock()
                with self.assertRaises(act.Stop):
                    op.recover()
                self.assertEqual(host.site.read_bytes(), b'concurrent operator routing')
                self.assertEqual(host.current.resolve(), host.backend)
                op.remove_new_frontend.assert_not_called()
                self.assertFalse((op.work / 'FRONTEND_ROLLED_BACK_AUTHENTICATED_BACKEND_RETAINED.json').exists())

    def test_old_pointer_alone_cannot_claim_a_successful_backend_recovery(self):
        host = LocalHost(self)
        op = host.operation()
        op.backend_attempted = True
        op.check_backend.side_effect = act.Stop('Fixture old runtime is not healthy')
        with self.assertRaises(act.Stop):
            op.recover()
        op.check_backend.assert_called_once_with(host.back_old)
        self.assertFalse((op.work / 'BACKEND_ROLLED_BACK_GPS_BLOCKED.json').exists())

    def test_persistence_preserves_retained_rows_and_restores_exact_bytes_after_partial_failure(self):
        host = LocalHost(self)
        op = host.operation()
        settings = copy.deepcopy(host.rows[0]['pm2_env']) | {
            'name': op.name, 'pm_cwd': str(host.frontend), 'pm_id': 2, 'instances': 1,
            'env': {'NODE_ENV': 'production', 'ACT_TRACKING_ACTIVATION': op.work.name, **op.public},
            'prev_restart_delay': 3000, '_tree_pids': [200],
        }
        row = {'name': op.name, 'pm_id': 2, 'pid': 200, 'pm2_env': settings}
        op.candidate_row = Mock(return_value=row)
        op.candidate_identity = act.pm2_identity(row)
        with patch.object(act, 'saved_matches_live', side_effect=act.Stop('Fixture saved-state readback failed')):
            with self.assertRaises(act.Stop):
                op.persist_frontend()
        self.assertTrue(op.dump_attempted)
        saved = json.loads(host.dump.read_bytes())
        self.assertEqual(saved[:-1], host.saved)
        self.assertEqual(saved[-1]['env']['ACT_TRACKING_ACTIVATION'], op.work.name)
        self.assertNotIn('instances', saved[-1])
        self.assertNotIn('pm_id', saved[-1])
        op.restore_dump()
        self.assertEqual(host.dump.read_bytes(), host.dump_before)
        self.assertEqual(stat.S_IMODE(host.dump.stat().st_mode), 0o600)

    def test_saved_state_concurrent_edit_is_not_overwritten_during_recovery(self):
        host = LocalHost(self)
        op = host.operation()
        op.dump_attempted = True
        op.dump_new_hash = act.sha(b'our prospective dump')
        host.dump.write_bytes(b'concurrent operator saved state')
        with self.assertRaises(act.Stop):
            op.restore_dump()
        self.assertEqual(host.dump.read_bytes(), b'concurrent operator saved state')


class EntryAndInterruptionChecks(unittest.TestCase):
    def test_cli_requires_explicit_activation_flag_and_record_before_any_host_access(self):
        for arguments in ([], ['--record', '/not-accessed'], ['--activate']):
            output = io.StringIO()
            with self.subTest(arguments=arguments), patch.object(act, 'Activation') as operation, patch.object(act, 'run') as run, patch.object(act.fcntl, 'flock') as flock, redirect_stdout(output), redirect_stderr(output):
                with self.assertRaises(SystemExit) as exit_code:
                    act.main(arguments)
                self.assertEqual(exit_code.exception.code, 2)
                operation.assert_not_called()
                run.assert_not_called()
                flock.assert_not_called()

    def main_patches(self, operation, lock, register_signal):
        stack = ExitStack()
        stack.enter_context(patch.object(act, 'Activation', return_value=operation))
        stack.enter_context(patch.object(act.Path, 'open', return_value=lock))
        stack.enter_context(patch.object(act.fcntl, 'flock'))
        stack.enter_context(patch.object(act.os, 'geteuid', return_value=0))
        stack.enter_context(patch.object(act.os, 'umask'))
        stack.enter_context(patch.object(act.os, 'chdir'))
        stack.enter_context(patch.object(act.signal, 'signal', side_effect=register_signal))
        return stack

    def test_operator_interrupt_recovers_under_lock_and_terminal_hangup_is_ignored(self):
        lock = io.StringIO()
        handlers = {}
        operation = Mock(phase='fixture activation phase', work=None)

        def register_signal(number, handler):
            handlers[number] = handler

        def interrupted_activation():
            handlers[act.signal.SIGTERM](act.signal.SIGTERM, None)

        def recovery():
            self.assertFalse(lock.closed)

        operation.activate.side_effect = interrupted_activation
        operation.recover.side_effect = recovery
        with self.main_patches(operation, lock, register_signal), patch.object(act, 'say'):
            code = act.main(['--activate', '--record', '/not-accessed'])
        self.assertEqual(code, 1)
        operation.recover.assert_called_once()
        self.assertEqual(handlers[act.signal.SIGHUP], act.signal.SIG_IGN)
        self.assertTrue(lock.closed)

    def test_closed_terminal_does_not_change_a_successful_main_result(self):
        lock = io.StringIO()
        operation = Mock(phase='complete', work=None)
        operation.activate.side_effect = lambda: act.say('Completed private activation receipt')
        with self.main_patches(operation, lock, lambda *_: None), patch('builtins.print', side_effect=BrokenPipeError('terminal gone')):
            code = act.main(['--activate', '--record', '/not-accessed'])
        self.assertEqual(code, 0)
        operation.recover.assert_not_called()

    def test_owned_child_is_reaped_on_timeout_before_transaction_recovery_can_begin(self):
        created = []
        popen = act.subprocess.Popen

        def capture(*args, **kwargs):
            self.assertTrue(kwargs['start_new_session'])
            child = popen(*args, **kwargs)
            created.append(child)
            return child

        with patch.object(act.subprocess, 'Popen', side_effect=capture):
            with self.assertRaises(subprocess.TimeoutExpired):
                act.run([sys.executable, '-c', 'import time; time.sleep(30)'], timeout=0.05)
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].poll())
        self.assertEqual(created[0].returncode, -act.signal.SIGKILL)


PM2_VM_SETUP = r'''
const __state={out:'',err:'',exit:null,calls:[],deletes:[],launchRPC:0,daemonStarts:0,closed:false};
globalThis.fixtureState=__state;
const __fields=['pm_cwd','pm_exec_path','exec_interpreter','args','exec_mode','env',
 'autorestart','restart_delay','max_restarts','min_uptime','status','restart_time','pm_uptime'];
const __policy={autorestart:true,restart_delay:3000,max_restarts:5,min_uptime:10000};
const __identity=p=>({name:p.name,pm_id:p.pm_id,pid:p.pid,
 ...Object.fromEntries(__fields.map(k=>[k,p.pm2_env[k]??null]))});
const __old=(name,id,port)=>({name,pm_id:id,pid:100+id,pm2_env:{
 name,pm_cwd:'/retained/'+name,pm_exec_path:'/retained/'+name+'/next',
 exec_interpreter:'/existing/node',args:['start','--hostname','127.0.0.1','--port',port],
 exec_mode:'fork_mode',env:{NODE_ENV:'production',KEEP_PRIVATE:'retained-fixture-secret'},
 ...__policy,status:'online',restart_time:0,pm_uptime:1000+id}});
const __rows=[__old('act',0,'3001'),__old('act-preview-892317f',1,'3002')];
const __original=JSON.parse(JSON.stringify(__rows));
const __config={name:'act-tracking-3a82c16',cwd:'/candidate/frontend',
 script:'/candidate/frontend/node_modules/next/dist/bin/next',interpreter:'/existing/node',
 args:['start','--hostname','127.0.0.1','--port','3003'],exec_mode:'fork',instances:1,
 env:{NODE_ENV:'production',ACT_TRACKING_ACTIVATION:'activation-owned',
 NEXT_PUBLIC_API_BASE_URL:'https://airportandcitytransfer.com',
 NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY:'pk_test_fixture_only',
 NEXT_PUBLIC_GOOGLE_MAPS_API_KEY:'maps-fixture-only'},...__policy};
const __input={socket:'/existing/rpc.sock',pid_file:'/existing/pm2.pid',daemon_pid:123,
 retained:JSON.parse(JSON.stringify(__rows.map(__identity))),identity_fields:__fields,
 config:__config,policy:__policy,
 name:__config.name,cwd:__config.cwd,script:__config.script,interpreter:__config.interpreter,
 args:__config.args,activation_nonce:'activation-owned',allow_absent:SCENARIO==='absent_acknowledged'};
globalThis.fixtureRows=__rows;
globalThis.fixtureOriginal=__original;
const __fakeFS={lstatSync:()=>({isSocket:()=>true}),existsSync:()=>true,
 readFileSync:(path)=>path===0?JSON.stringify(__input):'123'};
const __baseExecute=(method,data,cb)=>{
 __state.calls.push(method);
 if(method==='getMonitorData')return cb(null,__rows);
 if(method==='prepare'){
   const copy=JSON.parse(JSON.stringify(data));
   __rows.push({name:copy.name,pm_id:2,pid:102,pm2_env:{...copy,status:'online',restart_time:0,pm_uptime:1002}});
   return cb(null,[__rows[__rows.length-1]]);
 }
 throw Error('Unexpected underlying mutation '+method);
};
const __fakePM2={Client:{
 launchRPC:cb=>{__state.launchRPC++;cb(null);},
 start:()=>{__state.daemonStarts++;throw Error('Must not launch daemon');},
 launchDaemon:()=>{__state.daemonStarts++;throw Error('Must not launch daemon');},
 executeRemote:__baseExecute},
 list:cb=>__fakePM2.Client.executeRemote('getMonitorData',{},cb),
 start:(configuration,cb)=>{
   // SDK normalization can mutate its supplied config (for example exec_mode).
   // Add deletion of script too to prove the immutable expected definition is
   // independent even when a factory mutates its own app object aggressively.
   const app=configuration.apps[0];
   app.pm_cwd=app.cwd;app.pm_exec_path=app.script;delete app.script;
   app.exec_interpreter=app.interpreter;delete app.interpreter;
   app.exec_mode='fork_mode';app.env={HOME:'/home/act',...app.env};
   if(SCENARIO==='retained_drift')__rows[0].pm2_env.env.KEEP_PRIVATE='concurrent-change';
   if(SCENARIO==='wrong_launch')app.pm_cwd='/retained/act';
   if(SCENARIO==='lost_environment')delete app.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
   if(SCENARIO==='unapproved_method')return __fakePM2.Client.executeRemote('restartProcessId',0,cb);
   __fakePM2.Client.executeRemote('prepare',app,cb);
 },
 disconnect:cb=>{__state.closed=true;if(cb)cb();}
};
const __listeners={};
const __request={once:(name,fn)=>{__listeners[name]=fn;},close:()=>{__state.closed=true;},
 connect:()=>{__listeners.connect();}};
const __rpc={Client:class {constructor(){} call(method,data,cb){
 __state.calls.push(method);
 if(method==='getMonitorData')return cb(null,__rows);
 if(method==='deleteProcessId'){__state.deletes.push(data);return cb(null);}
 throw Error('Unexpected cleanup method '+method);
}}};
if(MODE==='remove'&&!SCENARIO.startsWith('absent')){
 const env={name:__config.name,pm_cwd:__config.cwd,pm_exec_path:__config.script,
 exec_interpreter:__config.interpreter,args:__config.args,
 env:{ACT_TRACKING_ACTIVATION:SCENARIO==='foreign'?'activation-foreign':'activation-owned'}};
 __rows.push({name:env.name,pm_id:2,pid:102,pm2_env:env});
}
function require(name){
 if(name==='fs')return __fakeFS;
 if(name==='util')return realRequire('node:util');
 if(name==='path')return realRequire('node:path');
 if(name==='/installed/pm2')return __fakePM2;
 if(name==='/installed/pm2/modules/pm2-axon')return {socket:()=>__request};
 if(name==='/installed/pm2/modules/pm2-axon-rpc')return __rpc;
 throw Error('Unexpected test dependency '+name);
}
const process={argv:['node','/installed/pm2'],kill:()=>{},
 stdout:{write:(text,cb)=>{__state.out+=text;if(cb)cb();}},
 stderr:{write:text=>{__state.err+=text;}},exit:code=>{__state.exit=code;}};
const console={log:()=>{}};
const setTimeout=()=>1,clearTimeout=()=>{};
'''


def run_pm2_vm(source, *, scenario, mode):
    harness = r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({realRequire:require,SCENARIO:SCENARIO_VALUE,MODE:MODE_VALUE});
(async()=>{
 await new vm.Script(SETUP_SOURCE+ACTUAL_SOURCE).runInContext(context);
 const state=context.fixtureState, rows=context.fixtureRows, originals=context.fixtureOriginal;
 assert.equal(state.daemonStarts,0);assert.equal(state.closed,true);
 assert.equal(state.out.includes('retained-fixture-secret'),false);
 assert.equal(state.out.includes('maps-fixture-only'),false);
 assert.equal(state.err.includes('retained-fixture-secret'),false);
 assert.equal(state.err.includes('maps-fixture-only'),false);
 if(MODE_VALUE==='start'){
   assert.equal(state.launchRPC,1);
   if(SCENARIO_VALUE==='good'){
     assert.equal(state.exit,0);
     assert.equal(state.calls.filter(x=>x==='prepare').length,1);
     assert.equal(rows.length,3);
     assert.equal(JSON.stringify(rows.slice(0,2)),JSON.stringify(originals));
     assert.equal(rows[2].pm2_env.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY,'maps-fixture-only');
     assert.equal(rows[2].pm2_env.env.ACT_TRACKING_ACTIVATION,'activation-owned');
     assert.equal(rows[2].pm2_env.env.KEEP_PRIVATE,undefined);
     assert.match(state.out,/^ACT_PM2_RESULT=\{"pm_id":2,"pid":102\}\n$/);
   }else{
     assert.equal(state.exit,2);
     assert.equal(state.calls.includes('prepare'),false);
     assert.equal(state.calls.includes('restartProcessId'),false);
     assert.equal(rows.length,2);
     assert.equal(state.out,'');
   }
 }else{
   assert.equal(JSON.stringify(rows.slice(0,2)),JSON.stringify(originals));
   if(SCENARIO_VALUE==='foreign'||SCENARIO_VALUE==='absent_unacknowledged'){
     assert.equal(state.exit,2);assert.equal(state.deletes.length,0);
   }else if(SCENARIO_VALUE==='absent_acknowledged'){
     assert.equal(state.exit,0);assert.equal(state.deletes.length,0);
   }else{
     assert.equal(state.exit,0);assert.equal(JSON.stringify(state.deletes),'[2]');
   }
 }
 process.stdout.write('VM checks passed\n');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    replacements = {'SCENARIO_VALUE': json.dumps(scenario), 'MODE_VALUE': json.dumps(mode),
                    'SETUP_SOURCE': json.dumps(PM2_VM_SETUP), 'ACTUAL_SOURCE': json.dumps(source)}
    for key, value in replacements.items():
        harness = harness.replace(key, value)
    result = subprocess.run(['node', '-'], input=harness, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    if result.stdout != 'VM checks passed\n':
        raise AssertionError('Unexpected VM output')


class PM2ProtocolChecks(unittest.TestCase):
    def test_start_preserves_retained_processes_and_environment_when_sdk_mutates_config(self):
        run_pm2_vm(act.PM2_START, scenario='good', mode='start')

    def test_start_refuses_concurrent_drift_wrong_definition_lost_environment_or_restart(self):
        for scenario in ('retained_drift', 'wrong_launch', 'lost_environment', 'unapproved_method'):
            with self.subTest(scenario=scenario):
                run_pm2_vm(act.PM2_START, scenario=scenario, mode='start')

    def test_cleanup_uses_activation_ownership_and_never_deletes_a_foreign_candidate(self):
        for scenario in ('owned', 'foreign', 'absent_unacknowledged', 'absent_acknowledged'):
            with self.subTest(scenario=scenario):
                run_pm2_vm(act.PM2_REMOVE_CANDIDATE, scenario=scenario, mode='remove')


if __name__ == '__main__':
    unittest.main(verbosity=2)
