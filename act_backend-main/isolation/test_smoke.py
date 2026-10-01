"""Real Django email/SQLite smoke tests; no ACT models or HTTP routes loaded."""
import os
import socket
import sys
import unittest


class IsolatedDjangoSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('DJANGO_SETTINGS_MODULE') != 'isolation.settings':
            raise RuntimeError('Use python -m isolation.run')
        import django
        django.setup()

    def test_email_captured_in_memory(self):
        from django.core import mail
        mail.get_connection()
        mail.outbox.clear()
        sent = mail.send_mail('Synthetic onboarding', 'Synthetic data only',
                              'test@example.invalid', ['driver@example.invalid'])
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['driver@example.invalid'])

    def test_disposable_synthetic_database(self):
        from django.db import connection
        self.assertEqual(connection.settings_dict['NAME'], ':memory:')
        with connection.cursor() as cursor:
            cursor.execute('CREATE TEMP TABLE synthetic_driver (id INTEGER, status TEXT)')
            try:
                cursor.execute('INSERT INTO synthetic_driver VALUES (%s, %s)', [1, 'pending'])
                cursor.execute('SELECT status FROM synthetic_driver WHERE id = %s', [1])
                self.assertEqual(cursor.fetchone(), ('pending',))
            finally:
                cursor.execute('DROP TABLE synthetic_driver')

    def test_python_network_tripwire(self):
        with self.assertRaisesRegex(RuntimeError, 'Network disabled'):
            socket.create_connection(('example.invalid', 443))

    def test_production_modules_not_loaded(self):
        self.assertFalse(any(k == 'myProject' or k.startswith('myProject.') for k in sys.modules))
        self.assertNotIn('firebase_admin', sys.modules)
        self.assertNotIn('stripe', sys.modules)
