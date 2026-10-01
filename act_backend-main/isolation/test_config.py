"""Host-side checks; requires PyYAML but not Django or Docker."""
import ast
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
import yaml

HERE = Path(__file__).resolve().parent


class IsolationConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load((HERE / 'compose.yaml').read_text())
        self.service = self.config['services']['tests']

    def test_no_runtime_network(self):
        self.assertEqual(self.service['network_mode'], 'none')
        self.assertEqual(list(self.config['services']), ['tests'])

    def test_no_host_access_or_credentials(self):
        for key in ('volumes', 'ports', 'env_file', 'environment', 'secrets', 'privileged', 'devices', 'pid', 'ipc'):
            self.assertNotIn(key, self.service)

    def test_restricted_runtime(self):
        self.assertTrue(self.service['read_only'])
        self.assertEqual(self.service['user'], '65534:65534')
        self.assertEqual(self.service['cap_drop'], ['ALL'])
        self.assertIn('no-new-privileges:true', self.service['security_opt'])

    def test_settings_are_constants_only(self):
        tree = ast.parse((HERE / 'settings.py').read_text())
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Expr):
                self.assertIsInstance(node.value, ast.Constant)
            else:
                self.assertIsInstance(node, ast.Assign)
                values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(values['DATABASES']['default']['NAME'], ':memory:')
        self.assertEqual(values['EMAIL_BACKEND'], 'django.core.mail.backends.locmem.EmailBackend')
        self.assertEqual(values['INSTALLED_APPS'], [])

    def test_build_context_allowlist(self):
        lines = (HERE / 'Dockerfile.dockerignore').read_text().splitlines()
        self.assertEqual(lines[0], '**')
        for line in lines[1:]:
            self.assertTrue(line.startswith('!'))
            self.assertNotIn('*', line)
            self.assertNotIn('.env', line)
            self.assertNotIn('myProject', line)
        dockerfile = (HERE / 'Dockerfile').read_text()
        self.assertNotIn('COPY . ', dockerfile)
        self.assertIn('USER 65534:65534', dockerfile)

    def test_guard_blocks_without_network_attempt(self):
        spec = importlib.util.spec_from_file_location('isolation_runner', HERE / 'run.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(socket.socket, 'connect'), patch.object(socket.socket, 'connect_ex'), \
             patch.object(socket.socket, 'sendto'), patch.object(socket, 'create_connection'), \
             patch.object(socket, 'getaddrinfo'):
            module.install_network_guard()
            for fn in (socket.create_connection, socket.getaddrinfo, socket.socket.connect,
                       socket.socket.connect_ex, socket.socket.sendto):
                with self.assertRaisesRegex(RuntimeError, 'Network disabled'):
                    fn()


if __name__ == '__main__':
    unittest.main()
