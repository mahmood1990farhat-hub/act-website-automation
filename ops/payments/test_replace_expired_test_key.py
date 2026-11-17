"""Local, synthetic safety tests. Never contacts Stripe or systemd."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

SOURCE = Path(__file__).with_name("replace_expired_test_key.py")
spec = importlib.util.spec_from_file_location("act_stripe_test_key_recovery", SOURCE)
recovery = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = recovery
spec.loader.exec_module(recovery)
OLD = "sk_test_" + "A" * 32
NEW = "sk_test_" + "B" * 32


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = self.root / ".env"
        self.original = ("SECRET_KEY=keep-django\r\nSTRIPE_WEBHOOK_SECRET=keep-webhook\r\n"
                         " export STRIPE_SECRET_KEY = '" + OLD + "' # keep comment\r\n"
                         "ANOTHER=value\r\n").encode()
        self.env.write_bytes(self.original)
        self.env.chmod(0o600)
        self.override = patch.object(recovery, "ENV_FILE", self.env)
        self.override.start()
        # Files remain real; only root ownership of these non-root-owned local
        # fixture directories is substituted. Runtime still requires UID 0.
        self.directory_override = patch.object(recovery, "root_directory")
        self.directory_override.start()

    def tearDown(self):
        self.override.stop()
        self.directory_override.stop()
        self.temp.cleanup()

    def test_replacement_preserves_every_other_byte_and_quotes(self):
        result = recovery.replacement_bytes(self.original, NEW)
        self.assertEqual(result, self.original.replace(OLD.encode(), NEW.encode()))
        self.assertEqual(recovery.key_span(result)[2], NEW)

    def test_missing_duplicate_or_live_old_assignment_refuses(self):
        bad = [b"OTHER=x\n", self.original + b"STRIPE_SECRET_KEY=" + OLD.encode(),
               self.original.replace(b"sk_test_", b"sk_live_")]
        for value in bad:
            with self.subTest(value=value[:10]), self.assertRaises(recovery.Refusal):
                recovery.key_span(value)

    def test_live_replacement_never_contacts_stripe(self):
        with patch.object(recovery, "stripe_get") as request:
            with self.assertRaisesRegex(recovery.Refusal, "REPLACEMENT_MUST_BE_TEST_SECRET"):
                recovery.validate_key("sk_live_" + "C" * 32)
            request.assert_not_called()

    def test_wrong_account_and_live_mode_refuse(self):
        for responses in [[{"id": "acct_other"}], [{"id": recovery.ACCOUNT}, {"livemode": True}]]:
            with self.subTest(responses=responses), patch.object(recovery, "stripe_get", side_effect=responses):
                with self.assertRaises(recovery.Refusal):
                    recovery.validate_key(NEW)

    def test_new_key_checks_only_expected_get_resources(self):
        with patch.object(recovery, "stripe_get", side_effect=[{"id": recovery.ACCOUNT}, {"livemode": False}]) as request:
            recovery.validate_key(NEW)
            self.assertEqual([call.args[0] for call in request.call_args_list], ["/v1/account", "/v1/balance"])

    def test_no_tty_never_prompts_for_secret(self):
        with patch.object(sys.stdin, "isatty", return_value=False), patch.object(recovery.getpass, "getpass") as prompt:
            with self.assertRaisesRegex(recovery.Refusal, "INTERACTIVE_TERMINAL_REQUIRED"):
                recovery.hidden_key()
            prompt.assert_not_called()

    def test_invalid_command_line_never_echoes_accidentally_pasted_secret(self):
        for arguments in [[NEW], ["--apply=" + NEW], ["--unknown", NEW]]:
            with self.subTest(argument_form=arguments[0].split("=")[0] if arguments[0].startswith("--") else "positional"):
                result = subprocess.run([sys.executable, str(SOURCE), *arguments],
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr,
                    "STOPPED: INVALID_ARGUMENTS_USE_CHECK_OR_APPLY_WITHOUT_KEY; STAGE=UNCHANGED\n")
                self.assertNotIn(NEW, result.stdout + result.stderr)

    def test_active_or_unknown_old_key_is_not_replaced(self):
        snapshot = recovery.read_env()
        for result in [(200, {"id": recovery.ACCOUNT}), (401, {"error": {"code": "invalid_api_key"}})]:
            with self.subTest(result=result), patch.object(recovery, "stripe_response", return_value=result):
                with self.assertRaisesRegex(recovery.Refusal, "EXISTING_KEY_NOT_CONFIRMED_EXPIRED"):
                    recovery.require_expired_current_key(snapshot)

    def test_expired_old_key_classified_without_printing_body(self):
        with patch.object(recovery, "stripe_response", return_value=(401, {"error": {"code": "api_key_expired", "message": OLD}})):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                recovery.require_expired_current_key(recovery.read_env())
            self.assertNotIn(OLD, output.getvalue())

    def test_concurrent_file_change_is_preserved(self):
        snapshot = recovery.read_env()
        newer = self.original + b"NEWER_WORK=preserve\n"
        self.env.write_bytes(newer)
        with self.assertRaisesRegex(recovery.Refusal, "ENV_CHANGED_NO_UPDATE"):
            recovery.atomic_replace(snapshot, recovery.replacement_bytes(snapshot.data, NEW))
        self.assertEqual(self.env.read_bytes(), newer)

    def test_extended_attributes_refuse_instead_of_being_dropped(self):
        with patch.object(recovery.os, "listxattr", return_value=["system.posix_acl_access"]):
            with self.assertRaisesRegex(recovery.Refusal, "ENV_EXTENDED_ATTRIBUTES_REQUIRE_REVIEW"):
                recovery.read_env()

    def test_attribute_check_failure_is_not_ignored(self):
        with patch.object(recovery.os, "listxattr", side_effect=OSError("not supported")):
            with self.assertRaisesRegex(recovery.Refusal, "ENV_ATTRIBUTE_CHECK_UNAVAILABLE"):
                recovery.read_env()

    def test_service_environment_source_must_be_proven(self):
        release = self.root / "releases" / "expected" / "backend"
        (release / "apps/trips").mkdir(parents=True)
        (release / ".env").symlink_to(self.env)
        (release / "release.json").write_text(json.dumps({"git_sha": recovery.BACKEND_SHA}))
        (release / "apps/trips/consumers.py").write_bytes(b"fixture consumer")
        current = self.root / "current"
        current.symlink_to(release)
        cwd = self.root / "proc-cwd"
        cwd.symlink_to(release)
        environ = self.root / "proc-environ"
        before = recovery.read_env()
        cases = [
            ("", "", b"", "django-shared-env"),
            ("", "", ("STRIPE_SECRET_KEY=" + OLD).encode(), None),
            (str(self.env) + " (ignore_errors=no)", "", ("STRIPE_SECRET_KEY=" + OLD).encode(), "systemd-shared-env"),
            ("/etc/unknown.env (ignore_errors=no)", "", b"", None),
            ("", "STRIPE_SECRET_KEY=" + OLD, b"", None),
        ]
        def local_path(value):
            return {"/proc/123/cwd": cwd, "/proc/123/environ": environ}.get(str(value), Path(value))
        for env_files, explicit_env, inherited, expected in cases:
            environ.write_bytes(inherited)
            properties = (f"ActiveState=active\nMainPID=123\nWorkingDirectory={current}\n"
                          f"EnvironmentFiles={env_files}\nEnvironment={explicit_env}")
            with self.subTest(source=expected, files=env_files), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(recovery, "CURRENT", current))
                stack.enter_context(patch.object(recovery, "Path", side_effect=local_path))
                stack.enter_context(patch.object(recovery, "CONSUMER_SHA256", hashlib.sha256(b"fixture consumer").hexdigest()))
                stack.enter_context(patch.object(recovery, "command", return_value=properties))
                if expected:
                    self.assertEqual(recovery.service_snapshot(before)["key_source"], expected)
                else:
                    with self.assertRaises(recovery.Refusal):
                        recovery.service_snapshot(before)

    def test_busy_existing_deployment_lock_stops_before_preflight_or_prompt(self):
        fd = os.open(self.root / "fixture-lock", os.O_RDWR | os.O_CREAT, 0o600)
        info = SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o600, st_nlink=1)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", [str(SOURCE), "--apply"]))
            stack.enter_context(patch.object(recovery.os, "geteuid", return_value=0))
            opened = stack.enter_context(patch.object(recovery.os, "open", return_value=fd))
            stack.enter_context(patch.object(recovery.os, "fstat", return_value=info))
            stack.enter_context(patch.object(recovery.fcntl, "flock", side_effect=BlockingIOError))
            read = stack.enter_context(patch.object(recovery, "read_env"))
            prompt = stack.enter_context(patch.object(recovery, "hidden_key"))
            with self.assertRaisesRegex(recovery.Refusal, "EXISTING_BACKEND_DEPLOYMENT_LOCK_BUSY_NO_UPDATE"):
                recovery.main()
            self.assertEqual(opened.call_args.args[0], Path("/run/lock/act-backend-deploy.lock"))
            read.assert_not_called()
            prompt.assert_not_called()

    def test_post_write_deployment_drift_stops_before_restart(self):
        snapshot = recovery.read_env()
        before = {"pid": 123, "release": "/expected", "key_source": "django-shared-env"}
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(recovery, "require_expired_current_key"))
            stack.enter_context(patch.object(recovery, "validate_key"))
            stack.enter_context(patch.object(recovery, "service_snapshot", side_effect=[before, {**before, "pid": 900}]))
            stack.enter_context(patch.object(recovery, "BACKUP_ROOT", self.root / "backup"))
            restart = stack.enter_context(patch.object(recovery.subprocess, "run"))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            with self.assertRaisesRegex(recovery.Refusal, "KEY_UPDATED_SERVICE_OR_ENV_CHANGED_NOT_RESTARTED"):
                recovery.apply(snapshot, before, 401, NEW)
            restart.assert_not_called()
            self.assertEqual(recovery.key_span(self.env.read_bytes())[2], NEW)

    def test_atomic_update_preserves_ownership_permissions_and_other_values(self):
        snapshot = recovery.read_env()
        result = recovery.replacement_bytes(snapshot.data, NEW)
        recovery.atomic_replace(snapshot, result)
        updated = self.env.stat()
        self.assertEqual(self.env.read_bytes(), result)
        self.assertEqual((updated.st_uid, updated.st_gid, stat.S_IMODE(updated.st_mode)),
                         (snapshot.uid, snapshot.gid, snapshot.mode))
        self.assertFalse(list(self.root.glob(".act-stripe-*")))

    def test_private_exclusive_backup_retains_original_bytes(self):
        with patch.object(recovery, "BACKUP_ROOT", self.root / "backup"):
            one = Path(recovery.backup(self.original))
            two = Path(recovery.backup(self.original))
        self.assertNotEqual(one, two)
        self.assertEqual(one.read_bytes(), self.original)
        self.assertEqual(stat.S_IMODE(one.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(one.parent.stat().st_mode), 0o700)

    def run_apply(self, restart_code=0, restart_exception=None):
        snapshot = recovery.read_env()
        before = {"pid": 123, "release": "/expected/release", "key_source": "django-shared-env"}
        after = {**before, "pid": 124}
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(recovery, "require_expired_current_key"))
            stack.enter_context(patch.object(recovery, "validate_key"))
            stack.enter_context(patch.object(recovery, "service_snapshot", side_effect=[before, before, after]))
            stack.enter_context(patch.object(recovery, "readiness", return_value=401))
            stack.enter_context(patch.object(recovery, "BACKUP_ROOT", self.root / "backup"))
            restarted = stack.enter_context(patch.object(recovery.subprocess, "run",
                side_effect=restart_exception, return_value=Mock(returncode=restart_code)))
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            error = None
            try:
                recovery.apply(snapshot, before, 401, NEW)
            except recovery.Refusal as failure:
                error = str(failure)
            self.assertEqual(restarted.call_count, 1)
            self.assertEqual(restarted.call_args.args[0], ["systemctl", "restart", "act.service"])
            self.assertEqual(self.env.read_bytes(), self.original.replace(OLD.encode(), NEW.encode()))
            backups = list((self.root / "backup").glob("*/backend.env.before"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), self.original)
            self.assertNotIn(OLD, output.getvalue())
            self.assertNotIn(NEW, output.getvalue())
            return error, output.getvalue()

    def test_success_does_not_claim_guest_checkout_passed(self):
        error, output = self.run_apply()
        self.assertIsNone(error)
        self.assertIn("APPLIED_RESTARTED_GUEST_CHECK_PENDING", output)

    def test_restart_failure_keeps_new_key_backup_and_does_not_restart_twice(self):
        error, _ = self.run_apply(restart_code=1)
        self.assertEqual(error, "KEY_UPDATED_RESTART_FAILED_BACKUP_RETAINED")

    def test_restart_timeout_does_not_retry_or_restore_expired_key(self):
        error, _ = self.run_apply(restart_exception=subprocess.TimeoutExpired(["systemctl"], 25))
        self.assertEqual(error, "KEY_UPDATED_RESTART_RESULT_UNKNOWN_BACKUP_RETAINED")


if __name__ == "__main__":
    unittest.main()
