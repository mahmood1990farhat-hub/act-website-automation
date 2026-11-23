"""Offline tests of adopting and finishing the already running Admin candidate.

Only temporary files are mutated. Process discovery, listeners, HTTP and Nginx
commands are mocked; the pinned prior atomic-file and manifest utilities are real.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True


def load_local(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


f = load_local("header_finish_test_target", "finish_admin_header_candidate.py")
fixtures = load_local("header_finish_test_fixtures", "test_admin_header_release.py")
menu_fixture, public_environment = fixtures.menu_fixture, fixtures.public_environment
OLD_PM2_ID, NEW_PM2_ID, OTHER_PM2_ID = fixtures.OLD_PM2_ID, fixtures.NEW_PM2_ID, fixtures.OTHER_PM2_ID

b = f.load_base()
SPEC = importlib.util.spec_from_file_location(
    "header_finish_prior_test", Path(__file__).parents[1] / "first-journey/passenger_frontend_release.py")
prior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)
if b.digest(Path(SPEC.origin).read_bytes()) != b.PRIOR_HASH:
    raise AssertionError("Offline atomic utility differs from the pinned prior helper")
Completion = f.completion_class(b)


def put(path, raw, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(mode)


def metadata(path):
    info = path.stat()
    return (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode),
            {name: os.getxattr(path, name) for name in os.listxattr(path)})


class HostFixture:
    """Real temporary artifacts; only unavailable host interfaces are substituted."""
    def __init__(self, stack):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.active, self.candidate = self.root / "active", self.root / "candidate"
        self.old_assets, self.new_assets = self.root / "old-assets", self.root / "new-assets"
        self.record, self.completion = self.root / "attempt", self.root / "completion"
        self.nginx = self.root / "nginx"
        self.site, self.master = self.nginx / "sites-enabled/act", self.nginx / "nginx.conf"
        self.dump, self.lock = self.root / "dump.pm2", self.root / "deployment.lock"
        self.record.mkdir(mode=0o700)
        paths = dict(ACTIVE=self.active, CANDIDATE=self.candidate, OLD_ASSETS=self.old_assets,
                     NEW_ASSETS=self.new_assets, RECORD=self.record, SITE=self.site,
                     MASTER=self.master, DUMP=self.dump, LOCK=self.lock)
        stack.enter_context(patch.multiple(b, **paths))
        stack.enter_context(patch.object(f, "COMPLETION_RECORD", self.completion))
        stack.enter_context(patch.object(prior, "SITE", self.site))
        # /etc/nginx containment and root ownership are host boundaries; all
        # underlying files and relative-path validation remain real and local.
        stack.enter_context(patch.object(f, "Path", side_effect=lambda value: self.nginx if value == "/etc/nginx" else Path(value)))
        stack.enter_context(patch.object(f.os, "geteuid", return_value=0))
        stack.enter_context(patch.object(f, "private_directory"))
        stack.enter_context(patch.object(f, "emit"))
        stack.enter_context(patch.object(b, "emit"))
        self.public = public_environment()
        self.backend = {"pointer": "releases/retained", "cwd": "/synthetic/backend", "service": {"MainPID": "901"}}
        for locale in ("en", "ar"):
            before, after = menu_fixture(locale)
            relative = f"src/dictionaries/{locale}/home.json"
            put(self.active / relative, before)
            put(self.candidate / relative, after)
        for root in (self.active, self.candidate):
            put(root / ".env", b"PRIVATE_EXISTING_SETTING=synthetic-private-value\n", 0o640)
            put(root / "package-lock.json", b'{"lockfileVersion":3}\n')
            put(root / "source.ts", b"unchanged application source\n")
        put(self.active / ".next/BUILD_ID", b.OLD_BUILD.encode())
        put(self.candidate / ".next/BUILD_ID", b"existing-candidate-build")
        key = self.public["NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY"].encode()
        put(self.active / ".next/static/chunks/old.js", b'"' + key + b'"; // old bundle')
        put(self.candidate / ".next/static/chunks/new.js", b'"' + key + b'"; // candidate bundle')
        put(self.old_assets / "chunks/old.js", (self.active / ".next/static/chunks/old.js").read_bytes())
        for source in (self.old_assets, self.candidate / ".next/static"):
            for relative in prior.tree(source):
                put(self.new_assets / relative, (source / relative).read_bytes())
        original = ("server {\n" + "".join(
            f" location /{name} {{\n  proxy_pass http://127.0.0.1:3005;\n }}\n"
            for name in ("", "en", "ar")) +
            f" location /_next/static/ {{\n  alias {self.old_assets}/;\n }}\n"
            " location /api/ { proxy_pass http://unix:/run/act.sock; }\n}\n").encode()
        put(self.site, original, 0o640)
        put(self.master, b"pid /run/nginx.pid;\nevents {}\nhttp {\n include /etc/nginx/sites-enabled/*;\n}\n")
        put(self.lock, b"")
        stack.enter_context(patch.object(b, "SITE_HASH", b.digest(original)))
        self.proposed, self.rollback = b.route_pair(original)
        runtime = dict(self.public, unique_id=OLD_PM2_ID, PORT="3005",
                       ACT_EXISTING_SETTING="preserve-me", PRIVATE_EXISTING_SETTING="synthetic-private-value")
        old_env = dict(name="retained-frontend", pm_cwd=str(self.active),
                       pm_exec_path=str(self.active / "node_modules/next/dist/bin/next"),
                       exec_interpreter=str(b.NODE), args=["start", "--hostname", "127.0.0.1", "--port", "3005"],
                       exec_mode="fork_mode", env=runtime, status="online", restart_time=0, pm_uptime=100, **prior.POLICY)
        self.old = {"name": old_env["name"], "pm_id": 2, "pid": 1001, "pm2_env": old_env}
        self.saved = [copy.deepcopy(old_env)]
        self.obj = Completion(prior)
        self.obj.current, self.obj.public = self.old, self.public
        config = self.obj.candidate_config()
        candidate_env = dict(name=b.NAME, pm_cwd=config["cwd"], pm_exec_path=config["script"],
                             exec_interpreter=config["interpreter"], args=config["args"], exec_mode="fork_mode",
                             env=dict(config["env"], unique_id=NEW_PM2_ID, PM2_ADDED_SETTING="retained"),
                             status="online", restart_time=0, pm_uptime=101, **prior.POLICY)
        self.row = {"name": b.NAME, "pm_id": 6, "pid": 1002, "pm2_env": candidate_env}
        self.rows = [self.old, self.row]
        self.original_rows = copy.deepcopy(self.rows)
        self.original_dump = b.packed(self.saved)
        put(self.dump, self.original_dump, 0o600)
        os.setxattr(self.site, "user.act.test", b"preserve-site-metadata")
        os.setxattr(self.dump, "user.act.test", b"preserve-dump-metadata")
        self.site_metadata, self.dump_metadata = metadata(self.site), metadata(self.dump)
        source, expected_source = b.source_tree(self.active), b.source_tree(self.candidate)
        plan = dict(patch_sha=b.PATCH_SHA, source_basis=str(self.active),
                    source_basis_sha256=b.digest(b.packed(source)), candidate_source_sha256=b.digest(b.packed(expected_source)),
                    old_build_id=b.OLD_BUILD, new_build_id="existing-candidate-build", candidate=str(self.candidate),
                    assets=str(self.new_assets), name=b.NAME, port=b.PORT, original_nginx_sha256=b.digest(original),
                    proposed_nginx_sha256=b.digest(self.proposed), rollback_nginx_sha256=b.digest(self.rollback),
                    public_environment_sha256=b.digest(b.packed(self.public)), backend=self.backend,
                    credentials_changed=False, source_is_active_copy_plus_approved_patch=True)
        records = {"nginx.before.conf": original, "nginx.proposed.conf": self.proposed,
                   "nginx.rollback.conf": self.rollback, "pm2.before.json": self.original_dump,
                   "source.before.json": b.packed(source), "public-environment.json": b.packed(self.public),
                   "plan.json": b.packed(plan), "05-pm2-start.log": b"Candidate startup refused or incomplete.\n"}
        for stage in f.EXPECTED_ATTEMPT_STAGES:
            records[stage + ".json"] = b.packed(dict(state=stage, patch_sha=b.PATCH_SHA,
                backend_modified=False, credentials_changed=False, payment_attempted=False))
        for relative, raw in records.items():
            put(self.record / relative, raw)
        self.record_before = prior.tree(self.record)
        self.obj.daemon_identity = (777, 1, 2)
        self.obj.rows = Mock(side_effect=lambda: self.rows)
        self.obj.backend = Mock(side_effect=lambda: self.backend)
        self.obj.public_environment = Mock(side_effect=b.extract_public_overrides)
        self.obj.listener = Mock()
        self.obj.other_nginx = Mock(return_value="unchanged-other-nginx-config")
        self.obj.command = Mock(side_effect=self.command)
        self.obj.verify_pages = Mock(return_value={"en": {"synthetic.js"}, "ar": {"synthetic.js"}})
        self.obj.verify_public = Mock()
        for name in ("prepare", "start", "unused_port"):
            setattr(self.obj, name, Mock(side_effect=AssertionError("Existing candidate must be reused")))

    @staticmethod
    def command(label, argv, **kwargs):
        allowed = {"completion-nginx-validate-proposed", "completion-nginx-validate-rollback",
                   "nginx-test-live", "nginx-reload", "completion-rollback-nginx-test",
                   "completion-rollback-nginx-reload"}
        if label not in allowed:
            raise AssertionError("Unexpected host operation: " + label)
        return b""

    def adopt(self):
        self.obj.adopt_existing()
        return self.obj


class FixtureTest(unittest.TestCase):
    def fixture(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        return HostFixture(stack)


class AdoptionAndDrift(FixtureTest):
    def test_exact_existing_candidate_is_adopted_without_writes_or_new_processes(self):
        h = self.fixture()
        obj = h.adopt()
        self.assertIsNone(obj.work)
        self.assertFalse(h.completion.exists())
        self.assertEqual(obj.candidate_unique_id, NEW_PM2_ID)
        self.assertEqual(obj.candidate_identity, prior.identity(h.row))
        self.assertEqual(h.rows, h.original_rows)
        self.assertEqual(prior.tree(h.record), h.record_before)
        self.assertEqual(h.dump.read_bytes(), h.original_dump)
        obj.command.assert_not_called()
        for name in ("prepare", "start", "unused_port"):
            getattr(obj, name).assert_not_called()

    def test_only_observed_pre_switch_journal_stages_are_accepted(self):
        h = self.fixture()
        self.assertEqual(f.attempt_stages(b, h.record), f.EXPECTED_ATTEMPT_STAGES)
        path = h.record / "CANDIDATE_START_ATTEMPTED.json"
        raw = path.read_bytes()
        path.unlink()
        with self.assertRaises(f.Stop):
            f.attempt_stages(b, h.record)
        put(path, raw)
        value = json.loads(raw); value["credentials_changed"] = True
        put(path, b.packed(value))
        with self.assertRaises(f.Stop):
            f.attempt_stages(b, h.record)
        put(path, raw)
        for stage in ("PM2_DUMP_WRITE_ATTEMPTED", "NGINX_SWITCH_ATTEMPTED", "ADMIN_HEADER_DEPLOYED", "ROLLBACK_STARTED"):
            with self.subTest(stage=stage):
                marker = h.record / (stage + ".json")
                put(marker, b.packed(dict(state=stage, patch_sha=b.PATCH_SHA, backend_modified=False,
                                         credentials_changed=False, payment_attempted=False)))
                with self.assertRaises(f.Stop):
                    h.obj.adopt_existing()
                marker.unlink()
        self.assertIsNone(h.obj.work)
        self.assertFalse(h.completion.exists())

    def test_adoption_refuses_source_public_backend_dump_and_route_drift(self):
        cases = ("active-source", "candidate-source", "public-env", "backend", "saved-dump", "route", "asset-union")
        for case in cases:
            with self.subTest(case=case), contextlib.ExitStack() as stack:
                h = HostFixture(stack)
                if case == "active-source":
                    put(h.active / "source.ts", b"changed")
                elif case == "candidate-source":
                    put(h.candidate / "source.ts", b"changed")
                elif case == "public-env":
                    h.obj.public_environment = Mock(return_value=dict(h.public, NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_stale"))
                elif case == "backend":
                    h.obj.backend = Mock(return_value={"changed": True})
                elif case == "saved-dump":
                    put(h.dump, b"changed")
                elif case == "route":
                    put(h.site, h.proposed)
                else:
                    put(h.new_assets / "chunks/new.js", b"changed")
                with self.assertRaises((f.Stop, b.Stop, prior.Stop)):
                    h.obj.adopt_existing()
                self.assertIsNone(h.obj.work)
                self.assertFalse(h.completion.exists())
                h.obj.command.assert_not_called()

    def test_candidate_launch_and_ownership_must_match_original_settings(self):
        for field in ("activation", "public", "private", "cwd", "args", "uuid"):
            with self.subTest(field=field), contextlib.ExitStack() as stack:
                h = HostFixture(stack)
                env = h.row["pm2_env"]
                if field == "activation": env["env"]["ACT_TRACKING_ACTIVATION"] = "/another/record"
                elif field == "public": env["env"]["NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY"] = "pk_test_stale"
                elif field == "private": env["env"]["PRIVATE_EXISTING_SETTING"] = "changed"
                elif field == "cwd": env["pm_cwd"] = "/another/release"
                elif field == "args": env["args"] = ["start", "--port", "3999"]
                else: env["env"]["unique_id"] = OLD_PM2_ID
                with self.assertRaises(b.Stop):
                    h.obj.adopt_existing()
                self.assertFalse(h.completion.exists())

    def test_retained_launch_or_inventory_changes_are_refused(self):
        h = self.fixture()
        self.assertEqual(f.validate_saved_rows(b, prior, h.rows, h.saved), [h.old])
        for mutate in (
            lambda rows: rows.append(copy.deepcopy(rows[0])),
            lambda rows: rows.pop(),
            lambda rows: rows[0]["pm2_env"]["env"].update(PRIVATE_EXISTING_SETTING="changed"),
            lambda rows: rows[0]["pm2_env"]["args"].append("changed"),
        ):
            rows = copy.deepcopy(h.rows); mutate(rows)
            with self.assertRaises(f.Stop):
                f.validate_saved_rows(b, prior, rows, h.saved)

    def test_guard_refuses_post_adoption_runtime_artifact_and_record_drift(self):
        for case in ("candidate-pid", "candidate-uuid", "extra-env", "retained-pid", "source", "assets", "record"):
            with self.subTest(case=case), contextlib.ExitStack() as stack:
                h = HostFixture(stack); obj = h.adopt()
                if case == "candidate-pid": h.row["pid"] += 1
                elif case == "candidate-uuid": h.row["pm2_env"]["env"]["unique_id"] = OTHER_PM2_ID
                elif case == "extra-env": h.row["pm2_env"]["env"]["PM2_ADDED_SETTING"] = "changed"
                elif case == "retained-pid": h.old["pid"] += 1
                elif case == "source": put(h.candidate / "source.ts", b"changed")
                elif case == "assets": put(h.new_assets / "chunks/new.js", b"changed")
                else: put(h.record / "05-pm2-start.log", b"changed")
                with self.assertRaises((f.Stop, b.Stop, prior.Stop)):
                    obj.guard(obj.original, candidate=True)

    def test_existing_completion_record_is_not_overwritten(self):
        h = self.fixture()
        h.completion.mkdir(mode=0o700)
        put(h.completion / "owner-record", b"preserve")
        with self.assertRaisesRegex(f.Stop, "COMPLETION_ALREADY_ATTEMPTED"):
            h.obj.adopt_existing()
        self.assertEqual((h.completion / "owner-record").read_bytes(), b"preserve")


class FinishAndRecovery(FixtureTest):
    def test_finish_reuses_candidate_preserves_runtime_environment_and_file_metadata(self):
        h = self.fixture(); obj = h.adopt()
        obj.finish()
        self.assertTrue(obj.complete)
        self.assertEqual(h.site.read_bytes(), h.proposed)
        persisted = json.loads(h.dump.read_bytes())
        self.assertEqual(persisted[:-1], h.saved)
        self.assertEqual(persisted[-1]["env"], h.original_rows[-1]["pm2_env"]["env"])
        self.assertEqual(metadata(h.site), h.site_metadata)
        self.assertEqual(metadata(h.dump), h.dump_metadata)
        self.assertEqual(h.rows, h.original_rows)
        self.assertEqual(prior.tree(h.record), h.record_before)
        self.assertEqual(prior.tree(h.completion / "original-attempt"), h.record_before)
        self.assertTrue((h.completion / "ADMIN_HEADER_DEPLOYED.json").exists())
        baseline = json.loads((h.completion / "continuation-baseline.json").read_bytes())
        self.assertFalse(baseline["candidate_started"])
        self.assertFalse(baseline["candidate_rebuilt"])
        for name in ("prepare", "start", "unused_port"):
            getattr(obj, name).assert_not_called()

    def test_failed_public_check_rolls_back_route_and_dump_without_candidate_cleanup(self):
        h = self.fixture(); obj = h.adopt()
        def verification(*, rollback=False):
            if not rollback:
                raise b.Stop("SYNTHETIC_PUBLIC_CHECK_FAILED")
        obj.verify_public.side_effect = verification
        with self.assertRaises(b.Stop):
            obj.finish()
        # The already owned process can fail/restart without blocking a return
        # to the retained old frontend. Its launch and UUID stay exact.
        h.row["pid"] = 0; h.row["pm2_env"]["status"] = "errored"
        obj.rollback()
        self.assertEqual(h.site.read_bytes(), h.rollback)
        self.assertEqual(h.dump.read_bytes(), h.original_dump)
        self.assertEqual(metadata(h.site), h.site_metadata)
        self.assertEqual(metadata(h.dump), h.dump_metadata)
        self.assertEqual(len(h.rows), 2)
        self.assertEqual(h.row["pm2_env"]["env"]["unique_id"], NEW_PM2_ID)
        self.assertEqual(prior.tree(h.record), h.record_before)
        self.assertTrue((h.completion / "PREVIOUS_FRONTEND_RESTORED.json").is_file())
        self.assertFalse(any("pm2" in call.args[0] for call in obj.command.call_args_list))

    def test_failed_check_before_persistence_changes_only_separate_completion_journal(self):
        h = self.fixture(); obj = h.adopt()
        obj.verify_pages.side_effect = b.Stop("SYNTHETIC_CANDIDATE_CHECK_FAILED")
        with self.assertRaises(b.Stop):
            obj.finish()
        obj.rollback()
        self.assertEqual(h.site.read_bytes(), obj.original)
        self.assertEqual(h.dump.read_bytes(), h.original_dump)
        self.assertEqual(h.rows, h.original_rows)
        self.assertEqual(prior.tree(h.record), h.record_before)
        self.assertTrue((h.completion / "COMPLETION_STOPPED_BEFORE_WRITES.json").is_file())
        self.assertEqual({call.args[0] for call in obj.command.call_args_list},
                         {"completion-nginx-validate-proposed", "completion-nginx-validate-rollback"})

    def test_rollback_refuses_unknown_route_or_dump_without_overwriting_it(self):
        for field in ("route", "dump"):
            with self.subTest(field=field), contextlib.ExitStack() as stack:
                h = HostFixture(stack); obj = h.adopt()
                obj.verify_public.side_effect = b.Stop("SYNTHETIC_PUBLIC_CHECK_FAILED")
                with self.assertRaises(b.Stop): obj.finish()
                path = h.site if field == "route" else h.dump
                put(path, b"another-operator-change")
                before_site, before_dump = h.site.read_bytes(), h.dump.read_bytes()
                calls = obj.command.call_count
                with self.assertRaises(f.Stop): obj.rollback()
                self.assertEqual(h.site.read_bytes(), before_site)
                self.assertEqual(h.dump.read_bytes(), before_dump)
                self.assertEqual(obj.command.call_count, calls)
                self.assertEqual(h.rows, h.original_rows)


class JournalAndCommandSafety(FixtureTest):
    def test_completion_status_prioritizes_recovery_over_deployment_marker(self):
        h = self.fixture()
        h.completion.mkdir(mode=0o700)
        for stage in ("ADMIN_HEADER_DEPLOYED", "ROLLBACK_STARTED", "PREVIOUS_FRONTEND_RESTORED"):
            with self.subTest(stage=stage):
                put(h.completion / (stage + ".json"), b.packed(dict(state=stage, patch_sha=b.PATCH_SHA)))
                before = prior.tree(h.completion)
                with patch.object(f, "emit") as output:
                    f.status(b)
                output.assert_any_call("RECORDED_ADMIN_HEADER_COMPLETION_STATUS: " + stage)
                self.assertEqual(prior.tree(h.completion), before)
        self.assertEqual(prior.tree(h.record), h.record_before)

    def test_recovery_failure_reports_only_fixed_codes_or_generic_substitutes(self):
        secret = "sk_test_SYNTHETIC_PRIVATE_VALUE"
        cases = (
            (b.Stop("PUBLIC_READINESS_FAILED"), f.Stop("ROLLBACK_NGINX_UNKNOWN"),
             "PUBLIC_READINESS_FAILED", "ROLLBACK_NGINX_UNKNOWN"),
            (RuntimeError(secret), ValueError(secret),
             "COMPLETION_OPERATION_FAILED", "COMPLETION_RECOVERY_FAILED"),
        )
        for operation, recovery, expected_operation, expected_recovery in cases:
            with self.subTest(expected_operation=expected_operation), contextlib.ExitStack() as stack:
                h = HostFixture(stack)
                h.obj.finish = Mock(side_effect=operation)
                h.obj.rollback = Mock(side_effect=recovery)
                with patch.object(f, "load_base", return_value=b), patch.object(b, "load_prior", return_value=prior), \
                     patch.object(f, "completion_class", return_value=lambda previous: h.obj), \
                     patch.object(f.signal, "signal"), patch.object(f.os, "umask"), patch.object(f, "emit") as output:
                    self.assertEqual(f.main(["--finish"]), 2)
                message = "\n".join(call.args[0] for call in output.call_args_list)
                self.assertIn("ORIGINAL_CODE=" + expected_operation, message)
                self.assertIn("RECOVERY_CODE=" + expected_recovery, message)
                self.assertNotIn(secret, message)
                h.obj.rollback.assert_called_once_with()

    def test_replaced_lock_is_refused_before_completion_mutations(self):
        for phase in ("after-flock", "during-adoption"):
            with self.subTest(phase=phase), contextlib.ExitStack() as stack:
                h = HostFixture(stack)
                real_flock = f.fcntl.flock
                real_adopt = h.obj.adopt_existing
                def replace_lock():
                    h.lock.rename(h.root / "held-old-lock")
                    put(h.lock, b"")
                def lock_then_replace(stream, flags):
                    real_flock(stream, flags)
                    replace_lock()
                def replace_then_adopt():
                    replace_lock()
                    real_adopt()
                h.obj.finish = Mock()
                h.obj.rollback = Mock()
                if phase == "after-flock":
                    stack.enter_context(patch.object(f.fcntl, "flock", side_effect=lock_then_replace))
                else:
                    h.obj.adopt_existing = Mock(side_effect=replace_then_adopt)
                with patch.object(f, "load_base", return_value=b), patch.object(b, "load_prior", return_value=prior), \
                     patch.object(f, "completion_class", return_value=lambda previous: h.obj), \
                     patch.object(f.signal, "signal"), patch.object(f.os, "umask"), patch.object(f, "emit") as output:
                    self.assertEqual(f.main(["--finish"]), 1)
                self.assertTrue(any("DEPLOYMENT_LOCK_REPLACED" in call.args[0] for call in output.call_args_list))
                h.obj.finish.assert_not_called()
                h.obj.rollback.assert_not_called()
                self.assertFalse(h.completion.exists())
                self.assertEqual(h.dump.read_bytes(), h.original_dump)


class FixedMessagesAndAssets(unittest.TestCase):
    def test_asset_union_preserves_old_and_new_and_refuses_collisions(self):
        self.assertEqual(f.merged_assets({"old.js": "old"}, {"new.js": "new"}),
                         {"old.js": "old", "new.js": "new"})
        with self.assertRaises(f.Stop):
            f.merged_assets({"same.js": "old"}, {"same.js": "different"})

    def test_bad_command_line_never_echoes_a_pasted_secret(self):
        secret = "sk_test_SYNTHETIC_PRIVATE_VALUE"
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(f, "load_base") as load:
            self.assertEqual(f.main(["--finish", secret]), 1)
        load.assert_not_called()
        self.assertNotIn(secret, output.getvalue())
        self.assertIn("EXPECTED_ONLY_FINISH_OR_STATUS", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
