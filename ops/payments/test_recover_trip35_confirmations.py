"""Synthetic safety and failure-mode tests, no live VPS/Stripe/Redis/SMTP."""
import io
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch, Mock
import recover_trip35_confirmations as x


class Trip35GuardTests(unittest.TestCase):
    def test_task_is_pinned_to_existing_paid_trip(self):
        self.assertIn('Trip.objects.get(pk=35)', x.DJANGO_READ)
        self.assertIn('Trip.objects.select_for_update', x.DJANGO_SEND)
        self.assertIn('t.is_guest_checkout is True and t.is_paid is True', x.DJANGO_SEND)
        self.assertIn("t.stripe_payment_intent == 'pi_3UcuauBxjYEaMc5N08BDzj38'", x.DJANGO_SEND)
        self.assertIn('passenger_confirmation_sent_at is None', x.DJANGO_SEND)
        self.assertIn('internal_booking_notification_sent_at is None', x.DJANGO_SEND)
        self.assertIn('assert not t.booking_confirmation_pdf', x.DJANGO_SEND)

    def test_direct_synchronous_task_no_celery_publish(self):
        self.assertIn('deliver_paid_booking_confirmations.run(35)', x.DJANGO_SEND)
        self.assertIn('request.called_directly is True', x.DJANGO_SEND)
        self.assertNotIn('.delay(', x.DJANGO_SEND)
        self.assertNotIn('.apply_async(', x.DJANGO_SEND)
        self.assertNotIn('Webhook', x.DJANGO_SEND)

    def test_guest_and_admin_email_settings_validated_before_sending(self):
        for code in (x.DJANGO_READ, x.DJANGO_SEND):
            self.assertIn('settings.ADMIN_EMAIL', code)
            self.assertIn('settings.EMAIL_HOST_USER', code)
            self.assertIn('validate_email(address)', code)
        self.assertIn('settings.EMAIL_HOST_PASSWORD', x.DJANGO_READ)

    def test_status_is_only_three_markers(self):
        self.assertIn('PDF_READY:', x.DJANGO_STATUS)
        self.assertIn('PASSENGER_EMAIL_RECORDED:', x.DJANGO_STATUS)
        self.assertIn('ADMIN_EMAIL_RECORDED:', x.DJANGO_STATUS)
        self.assertNotIn('passenger_email', x.DJANGO_STATUS)

    def test_git_blob_matches_real_git_sha(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'file.py';p.write_text('hello\n')
            self.assertEqual(x.git_blob(p), 'ce013625030ba8dba906f756967f9e9ca394464a')

    def test_resolve_storage_only_shared_symlink_and_exact_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            current=root/'releases/current';worker=root/'releases/worker'
            for p in (current,worker):p.mkdir(parents=True)
            shared=root/'shared/media/trips/booking_confirmations';shared.mkdir(parents=True)
            for p in (current,worker): (p/'media').symlink_to(root/'shared/media')
            with patch.object(x,'BACK',root),patch.object(x,'RELEASES',root/'releases'):
                self.assertEqual(x.resolve_storage(current,worker),shared)
                (worker/'media').unlink()
                wrong=root/'separate/media/trips/booking_confirmations';wrong.mkdir(parents=True)
                (worker/'media').symlink_to(root/'separate/media')
                with self.assertRaisesRegex(x.Stop,'MEDIA_NOT_SHARED'):
                    x.resolve_storage(current,worker)

    def test_symlinked_pdf_directory_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            current=root/'releases/current';worker=root/'releases/worker'
            for p in (current,worker):p.mkdir(parents=True)
            shared=root/'shared/media/trips';shared.mkdir(parents=True)
            actual=root/'shared/destination';actual.mkdir()
            (shared/'booking_confirmations').symlink_to(actual)
            for p in (current,worker):(p/'media').symlink_to(root/'shared/media')
            with patch.object(x,'BACK',root),patch.object(x,'RELEASES',root/'releases'):
                with self.assertRaisesRegex(x.Stop,'BOOKING_PDF_DIRECTORY_IDENTITY_CHANGED'):
                    x.resolve_storage(current,worker)

    def test_guard_record_is_exclusive_and_root_private(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'receipt'
            x.write_new(p,b'record')
            self.assertEqual(p.read_bytes(),b'record')
            self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            with self.assertRaises(FileExistsError): x.write_new(p,b'overwrite')

    def test_grant_group_fallback_changes_only_exact_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);target=root/'booking_confirmations';target.mkdir()
            target.chmod(0o755)
            record=root/'receipt';record.mkdir()
            orig=target.stat(); parent_before=root.stat()
            www_group = __import__('grp').getgrnam('www-data').gr_gid
            with patch.object(x,'RECORD',record),patch.object(x.shutil,'which',return_value=None),\
                 patch.object(x,'can_write',return_value=True):
                method=x.grant_storage(target,orig)
            self.assertEqual(method,'GROUP_WWW_DATA_SETGID')
            self.assertEqual(target.stat().st_gid,www_group)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode),0o2775)
            self.assertEqual(root.stat().st_mode,parent_before.st_mode)
            self.assertTrue((record/'PDF_STORAGE_WRITE_ACCESS_GRANTED.json').is_file())

    def test_acl_method_changes_only_specific_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);target=root/'booking_confirmations';target.mkdir()
            record=root/'receipt';record.mkdir()
            orig=target.stat()
            with patch.object(x,'RECORD',record),\
                 patch.object(x.shutil,'which',side_effect=lambda n:f'/usr/bin/{n}'),\
                 patch.object(x,'command',side_effect=[Mock(returncode=0,stdout=b'user::rwx\n'),Mock(returncode=0,stdout=b'')]) as cmd,\
                 patch.object(x,'can_write',return_value=True):
                method=x.grant_storage(target,orig)
            self.assertEqual(method,'ACL_USER_WWW_DATA')
            self.assertEqual((record/'original-directory.acl').read_bytes(),b'user::rwx\n')
            self.assertEqual(cmd.call_args_list[1].args[0][1:3], ['-m','u:www-data:rwx'])

    def test_acl_error_stops_without_fallback_to_group_chown(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);target=root/'pdf';target.mkdir();record=root/'receipt';record.mkdir()
            with patch.object(x,'RECORD',record),\
                 patch.object(x.shutil,'which',side_effect=lambda n:f'/usr/bin/{n}'),\
                 patch.object(x,'command',side_effect=[Mock(returncode=0,stdout=b'original'),Mock(returncode=1,stdout=b'')]),\
                 patch.object(x.os,'chown') as chown:
                with self.assertRaisesRegex(x.Stop,'PDF_DIRECTORY_ACL_UPDATE_FAILED'):
                    x.grant_storage(target,target.stat())
            chown.assert_not_called()

    def test_read_only_check_emits_no_email_sent_status(self):
        with patch.object(x,'source_and_directory_snapshot',return_value=(Path('/tmp'),None,Path('/tmp'),None)),\
             patch.object(x,'django',return_value=Mock(returncode=0,stdout=b'PASS: EXACT_PAID_GUEST_TRIP_35_AND_SMTP_CONFIG_CHECKED')) as dg,\
             patch('sys.stdout',new_callable=io.StringIO) as out:
            x.check()
        self.assertIn('NO_CHANGES; NO_EMAILS_SENT',out.getvalue())
        dg.assert_called_once()
        self.assertTrue(dg.call_args.kwargs['readonly'])

    def test_apply_requires_interactive_root_operator_before_modifying(self):
        with patch.object(x.sys.stdin,'isatty',return_value=False),\
             patch.object(x,'check') as check,patch.object(x,'grant_storage') as grant:
            with self.assertRaisesRegex(x.Stop,'ROOT_INTERACTIVE_OWNER_TERMINAL_REQUIRED'):
                x.apply()
        check.assert_not_called();grant.assert_not_called()

    def test_wrong_phrase_never_creates_record_or_calls_email(self):
        with patch.object(x.sys.stdin,'isatty',return_value=True),\
             patch.object(x.sys.stderr,'isatty',return_value=True),\
             patch.object(x,'check',return_value=(Path('/tmp'),Path('/tmp'),Mock())),\
             patch('builtins.input',return_value='WRONG'),\
             patch.object(x,'grant_storage') as grant, patch.object(x,'django') as dg:
            with self.assertRaisesRegex(x.Stop,'APPROVAL_PHRASE_DIFFERENT_NO_CHANGES'):
                x.apply()
        grant.assert_not_called();dg.assert_not_called()

    def test_approved_flow_records_pre_send_marker_and_success_once(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rec=root/'record';lock=root/'lock';lock.write_text('')
            target=root/'pdf';target.mkdir()
            with patch.object(x,'RECORD',rec),patch.object(x,'LOCK',lock),\
                 patch.object(x.sys.stdin,'isatty',return_value=True),\
                 patch.object(x.sys.stderr,'isatty',return_value=True),\
                 patch.object(x,'check',return_value=(root,target,target.stat())),\
                 patch('builtins.input',return_value=x.PHRASE),\
                 patch.object(x,'grant_storage',return_value='ACL_USER_WWW_DATA') as grant,\
                 patch.object(x,'django',return_value=Mock(returncode=0,stdout=b'PASS: TRIP35_PDF_AND_BOTH_SMTP_ACCEPTANCE_MARKERS')) as dg,\
                 patch('sys.stdout',new_callable=io.StringIO) as out:
                self.assertEqual(x.apply(),0)
            self.assertTrue((rec/'TRIP35_EMAIL_RECOVERY_ATTEMPT_STARTED.json').is_file())
            self.assertTrue((rec/'RECOVERY_REPORTED_SMTP_ACCEPTED.json').is_file())
            self.assertEqual(grant.call_count,1)
            self.assertEqual(dg.call_count,1)
            self.assertIn('NO_NEW_BOOKING_OR_PAYMENT; NO_QUEUE_CHANGES',out.getvalue())

    def test_failed_send_leaves_permanent_no_retry_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rec=root/'record';lock=root/'lock';lock.write_text('')
            target=root/'pdf';target.mkdir()
            with patch.object(x,'RECORD',rec),patch.object(x,'LOCK',lock),\
                 patch.object(x.sys.stdin,'isatty',return_value=True),\
                 patch.object(x.sys.stderr,'isatty',return_value=True),\
                 patch.object(x,'check',return_value=(root,target,target.stat())),\
                 patch('builtins.input',return_value=x.PHRASE),\
                 patch.object(x,'grant_storage',return_value='ACL_USER_WWW_DATA'),\
                 patch.object(x,'django',return_value=Mock(returncode=1,stdout=b'TRIP35_FAILURE_CLASS: PermissionError\n')) as dg,\
                 patch('sys.stdout',new_callable=io.StringIO) as out:
                self.assertEqual(x.apply(),2)
            self.assertTrue((rec/'TRIP35_EMAIL_RECOVERY_ATTEMPT_STARTED.json').is_file())
            self.assertTrue((rec/'RECOVERY_UNVERIFIED_NO_RETRY.json').is_file())
            self.assertIn('RECOVERY_FAILURE_CLASS: PermissionError',out.getvalue())
            self.assertNotIn('RECOVERY_REPORTED_SMTP_ACCEPTED',str(list(rec.iterdir())))

    def test_recovery_state_flag_no_queue_or_stripe_write(self):
        source=Path(x.__file__).read_text()
        self.assertNotIn('stripe.PaymentIntent.create(',source)
        self.assertNotIn('stripe.PaymentIntent.modify(',source)
        self.assertNotIn('apply_async(',source)
        self.assertNotIn('flushdb(',source)
        self.assertNotIn('systemctl", "restart',source)
        self.assertNotIn('celery worker',source)


if __name__=='__main__':
    unittest.main()
