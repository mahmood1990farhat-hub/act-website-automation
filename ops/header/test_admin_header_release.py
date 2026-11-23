"""Focused offline release checks: no VPS, provider, PM2 or Nginx calls.

Menu fixtures are the reviewed application files in this checkout. Host command
boundaries are mocked where exercised; temporary directories contain synthetic
configuration and keys only.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location(
    "admin_header_release", Path(__file__).with_name("admin_header_release.py"))
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)

ROOT = Path(__file__).resolve().parents[2]
TEST_KEY = "pk_test_" + "T" * 40
STALE_KEY = "pk_test_" + "S" * 40
LIVE_KEY = "pk_live_" + "L" * 40
OLD_PM2_ID = "11111111-1111-4111-8111-111111111111"
NEW_PM2_ID = "22222222-2222-4222-8222-222222222222"
OTHER_PM2_ID = "33333333-3333-4333-8333-333333333333"
EXPECTED_BEFORE = {
    "en": "2f0b301b1f607e162321c6f4d911f6f503da130286728b465fa453562ea803b8",
    "ar": "d87bf013da744564cb81ded97843d8df6d7704f14ed80bfea4004bddceeed7f9",
}
EXPECTED_AFTER = {
    "en": "a6d114637a04bd19c6c5e040ec0aa8a39d14e96754a028fb697cb0e7d04898b5",
    "ar": "74d793c730338dae888c65fe3dcf5323f8249e661ea5fc3c05fa494898ec64f8",
}


def menu_fixture(locale):
    """Read approved target; recover preimage independently of helper logic."""
    after = (ROOT / f"act_website-main/src/dictionaries/{locale}/home.json").read_bytes()
    label = "Admin" if locale == "en" else "الإدارة"
    entry = (
        '      {\n'
        f'        "name": "{label}",\n'
        f'        "url": "/{locale}/admin",\n'
        '        "protected": false\n'
        '      },\n'
    ).encode()
    if after.count(entry) != 1:
        raise AssertionError("Reviewed Admin fixture is absent or duplicated")
    before = after.replace(entry, b"", 1)
    if m.digest(before) != EXPECTED_BEFORE[locale] or m.digest(after) != EXPECTED_AFTER[locale]:
        raise AssertionError("Test fixture differs from reviewed application bytes")
    return before, after


def public_environment(key=TEST_KEY):
    return {
        "NEXT_PUBLIC_API_BASE_URL": "https://airportandcitytransfer.com",
        "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY": key,
        "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY": "AIza" + "A" * 35,
        "NEXT_PUBLIC_GOOGLE_ADS_ID": "AW-00000000000",
    }


def nginx_fixture():
    return (
        b"server {\n"
        b"    # Unrelated backend, timeouts and headers must remain byte-identical.\n"
        b"    location /api/ { proxy_pass http://unix:/run/act.sock; }\n"
        b"    location / {\n        proxy_pass http://127.0.0.1:3005;\n    }\n"
        b"    location /en {\n\tproxy_pass http://127.0.0.1:3005;\n    }\n"
        b"    location /ar {\n    proxy_pass http://127.0.0.1:3005;\n    }\n"
        b"    location /_next/static/ {\n        alias "
        + str(m.OLD_ASSETS).encode() + b"/;\n    }\n"
        b"    add_header X-Test unchanged;\n}\n"
    )


class MenuPreservation(unittest.TestCase):
    def test_only_approved_menu_item_is_added_in_each_language(self):
        for locale in ("en", "ar"):
            with self.subTest(locale=locale):
                before, expected = menu_fixture(locale)
                actual = m.patch_menu(before, locale)
                self.assertEqual(actual, expected)
                self.assertEqual(m.digest(actual), EXPECTED_AFTER[locale])
                original = json.loads(before)
                changed = json.loads(actual)
                links = changed["navbar"]["navLinks"]
                at = next(i for i, link in enumerate(links) if link["url"] == f"/{locale}/admin")
                self.assertEqual(links[at - 1]["url"], f"/{locale}/download-app")
                self.assertIs(links[at]["protected"], False)
                links.pop(at)
                self.assertEqual(changed, original)

    def test_source_drift_even_with_same_json_value_is_refused(self):
        before, _ = menu_fixture("en")
        drifted = before + b"\n"
        self.assertEqual(json.loads(before), json.loads(drifted))
        with self.assertRaises(m.Stop):
            m.patch_menu(drifted, "en")

    def test_existing_admin_entry_is_not_applied_twice(self):
        for locale in ("en", "ar"):
            with self.subTest(locale=locale), self.assertRaises(m.Stop):
                m.patch_menu(menu_fixture(locale)[1], locale)

    def test_unreviewed_language_is_refused(self):
        with self.assertRaises(m.Stop):
            m.patch_menu(menu_fixture("en")[0], "fr")


class RoutePreservation(unittest.TestCase):
    def test_switch_changes_only_three_upstreams_and_one_asset_alias(self):
        original = nginx_fixture()
        proposed, rollback = m.route_pair(original)
        union = original.replace(str(m.OLD_ASSETS).encode(), str(m.NEW_ASSETS).encode())
        self.assertEqual(proposed, union.replace(b"127.0.0.1:3005", b"127.0.0.1:3006"))
        self.assertEqual(rollback, union)
        self.assertIn(b"proxy_pass http://unix:/run/act.sock;", proposed)
        self.assertIn(b"add_header X-Test unchanged;", proposed)

    def test_rollback_keeps_new_asset_union_for_cached_candidate_html(self):
        _, rollback = m.route_pair(nginx_fixture())
        self.assertEqual(rollback.count(b"127.0.0.1:3005"), 3)
        self.assertNotIn(b"127.0.0.1:3006", rollback)
        self.assertIn(str(m.NEW_ASSETS).encode(), rollback)
        self.assertNotIn(str(m.OLD_ASSETS).encode(), rollback)

    def test_unexpected_route_count_is_refused(self):
        original = nginx_fixture()
        cases = [
            original.replace(b"127.0.0.1:3005", b"127.0.0.1:3004", 1),
            original + b"proxy_pass http://127.0.0.1:3005;\n",
            original.replace(b"127.0.0.1:3005", b"127.0.0.1:3006"),
        ]
        for blob in cases:
            with self.subTest(blob=blob[-60:]), self.assertRaises(m.Stop):
                m.route_pair(blob)

    def test_missing_or_duplicate_asset_alias_is_refused(self):
        original = nginx_fixture()
        alias = b"alias " + str(m.OLD_ASSETS).encode() + b"/;"
        for blob in (
            original.replace(alias, b"alias /unreviewed/assets/;"),
            original + alias + b"\n",
        ):
            with self.assertRaises(m.Stop):
                m.route_pair(blob)


class PaymentConfigurationPreservation(unittest.TestCase):
    def test_public_overrides_preserve_current_values_and_exclude_private_fields(self):
        public = public_environment()
        row = {"pm2_env": {
            **public, "PRIVATE_SECRET": "must-not-be-returned",
            "env": {**public, "OTHER_SECRET": "also-private"},
        }}
        self.assertEqual(m.extract_public_overrides(row), public)

    def test_conflicting_current_public_overrides_are_refused(self):
        public = public_environment()
        row = {"pm2_env": {
            **public,
            "env": {**public, "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY": STALE_KEY},
        }}
        with self.assertRaises(m.Stop):
            m.extract_public_overrides(row)

    def test_nonstring_public_override_is_refused(self):
        row = {"pm2_env": {"env": {"NEXT_PUBLIC_OPTION": 123}}}
        with self.assertRaises(m.Stop):
            m.extract_public_overrides(row)

    def test_current_test_configuration_is_preserved_in_full(self):
        public = public_environment()
        public["NEXT_PUBLIC_CUSTOM_EXISTING_OPTION"] = "retained"
        result = m.validate_public(public, {TEST_KEY.encode()})
        self.assertEqual(result, public)
        self.assertEqual(result["NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY"], TEST_KEY)

    def test_stale_live_missing_and_ambiguous_keys_are_refused(self):
        cases = [
            (public_environment(STALE_KEY), {TEST_KEY.encode()}),
            (public_environment(LIVE_KEY), {LIVE_KEY.encode()}),
            (public_environment(), set()),
            (public_environment(), {TEST_KEY.encode(), STALE_KEY.encode()}),
            (public_environment(), {TEST_KEY.encode(), LIVE_KEY.encode()}),
            (public_environment(""), {TEST_KEY.encode()}),
        ]
        for public, compiled in cases:
            with self.subTest(key_type=public["NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY"][:8], count=len(compiled)):
                with self.assertRaises(m.Stop):
                    m.validate_public(public, compiled)

    def test_unreviewed_api_origin_is_refused(self):
        public = public_environment()
        public["NEXT_PUBLIC_API_BASE_URL"] = "https://unrelated.example.invalid"
        with self.assertRaises(m.Stop):
            m.validate_public(public, {TEST_KEY.encode()})

    def test_compiled_key_scan_detects_multiple_and_live_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            js = root / ".next/static/chunks/app.js"
            js.parent.mkdir(parents=True)
            js.write_text(f'const first="{TEST_KEY}";const again="{TEST_KEY}";')
            self.assertEqual(m.compiled_keys(root), {TEST_KEY.encode()})
            js.write_text(f'const first="{TEST_KEY}";const second="{LIVE_KEY}";')
            self.assertEqual(m.compiled_keys(root), {TEST_KEY.encode(), LIVE_KEY.encode()})

    def test_compiled_key_scan_rejects_linked_javascript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside.js"
            outside.write_text(f'const key="{TEST_KEY}";')
            js = root / ".next/static/chunks/app.js"
            js.parent.mkdir(parents=True)
            js.symlink_to(outside)
            with self.assertRaises(m.Stop):
                m.compiled_keys(root)


class PrivateRecordSafety(unittest.TestCase):
    def test_private_write_is_exclusive_and_does_not_replace_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            m.write_new(path, b"original")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises((FileExistsError, m.Stop)):
                m.write_new(path, b"replacement")
            self.assertEqual(path.read_bytes(), b"original")

    def test_private_write_refuses_existing_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"; original.write_bytes(b"preserved")
            record = root / "record"; record.symlink_to(original)
            with self.assertRaises((FileExistsError, m.Stop)):
                m.write_new(record, b"replacement")
            self.assertEqual(original.read_bytes(), b"preserved")

    def test_source_manifest_preserves_application_environment_and_lockfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "src/untouched.ts": b"source",
                "package-lock.json": b"locked dependencies",
                ".env.production.local": b"synthetic configuration",
                "node_modules/dependency/index.js": b"installed dependency",
                ".next/static/chunk.js": b"generated bundle",
                "next-env.d.ts": b"generated types",
                "tsconfig.tsbuildinfo": b"incremental cache",
            }
            for name, content in files.items():
                file = root / name; file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(content)
            self.assertEqual(m.source_tree(root), {
                name: m.digest(files[name])
                for name in ("src/untouched.ts", "package-lock.json", ".env.production.local")
            })
            (root / "package-lock.json").write_bytes(b"new dependency lock")
            self.assertNotEqual(m.source_tree(root)["package-lock.json"], m.digest(files["package-lock.json"]))

    def test_source_manifest_refuses_linked_application_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            original = root / "original.ts"; original.write_bytes(b"source")
            (root / "src/link.ts").symlink_to(original)
            with self.assertRaises(m.Stop):
                m.source_tree(root)


class HtmlAndFailureSafety(unittest.TestCase):
    def html(self, locale, count=2, label=None):
        name = label if label is not None else m.LABELS[locale]
        links = ''.join(f'<a href="/{locale}/admin">{name}</a>' for _ in range(count))
        return (
            '<html><head><script src="/_next/static/chunks/one.js"></script>'
            '<link rel="stylesheet" href="/_next/static/css/one.css"></head>'
            f'<body>synthetic-build{links}</body></html>'
        ).encode()

    def test_rendered_check_requires_both_menus_and_correct_language_label(self):
        for locale in ("en", "ar"):
            with self.subTest(locale=locale):
                self.assertEqual(m.assert_menu_html(self.html(locale), locale, "synthetic-build"), {
                    "/_next/static/chunks/one.js", "/_next/static/css/one.css",
                })
                for html in (self.html(locale, 1), self.html(locale, 3), self.html(locale, label="Wrong label")):
                    with self.assertRaises(m.Stop):
                        m.assert_menu_html(html, locale, "synthetic-build")

    def test_old_build_missing_link_and_unsafe_asset_are_refused(self):
        with self.assertRaises(m.Stop):
            m.assert_menu_html(self.html("en"), "en", "a-different-build")
        with self.assertRaises(m.Stop):
            m.assert_menu_html(self.html("en", 0), "en", "synthetic-build")
        bad = self.html("en").replace(b"/chunks/one.js", b"/../private.js")
        with self.assertRaises(m.Stop):
            m.assert_menu_html(bad, "en", "synthetic-build")
        # A rollback check deliberately expects the unchanged old menus.
        m.assert_menu_html(self.html("en", 0), "en", "synthetic-build", has_admin=False)

    def test_bad_cli_argument_does_not_echo_a_pasted_secret(self):
        secret = "sk_test_" + "PRIVATE_SYNTHETIC_VALUE" * 3
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), patch.object(m, "load_prior") as prior:
            self.assertEqual(m.main(["--deploy=" + secret]), 1)
        prior.assert_not_called()
        self.assertNotIn(secret, out.getvalue())
        self.assertIn("EXPECTED_ONLY_CHECK_DEPLOY_OR_STATUS", out.getvalue())

    def test_unexpected_preflight_exception_never_echoes_configuration(self):
        secret = "sk_test_" + "PRIVATE_SYNTHETIC_VALUE" * 3
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(m.os, "geteuid", return_value=0), \
             patch.object(m.os, "umask"), patch.object(m, "load_prior", side_effect=RuntimeError(secret)):
            self.assertEqual(m.main(["--check"]), 1)
        self.assertNotIn(secret, out.getvalue())
        self.assertIn("NO_SECRET_DETAILS_PRINTED", out.getvalue())

    def test_status_reports_recovery_after_a_deployed_marker_without_mutating_records(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory)
            record.chmod(0o700)
            real_stat = Path.stat

            def root_owned_record(path, *args, **kwargs):
                # The journal priority check is also runnable as an ordinary user.
                actual = real_stat(path, *args, **kwargs)
                if path == record:
                    fields = list(actual)
                    fields[4] = 0
                    return os.stat_result(fields)
                return actual

            for stage in ("ADMIN_HEADER_DEPLOYED", "ROLLBACK_STARTED", "PREVIOUS_FRONTEND_RESTORED"):
                with self.subTest(stage=stage):
                    m.write_new(record / (stage + ".json"), json.dumps({
                        "state": stage, "patch_sha": m.PATCH_SHA,
                    }).encode())
                    before = {path.name: path.read_bytes() for path in record.iterdir()}
                    with patch.object(m, "RECORD", record), patch.object(m, "emit") as emitted, \
                         patch.object(Path, "stat", new=root_owned_record):
                        m.status()
                    emitted.assert_any_call("RECORDED_ADMIN_HEADER_STATUS: " + stage)
                    self.assertEqual(before, {path.name: path.read_bytes() for path in record.iterdir()})


class RollbackOwnership(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        record = root / "record"; record.mkdir()
        site = root / "site.conf"; site.write_bytes(b"candidate-route")
        dump = root / "dump.pm2"; dump.write_bytes(b"candidate-dump")
        writes = []
        def atomic_file(path, data, expected):
            self.assertEqual(m.digest(path.read_bytes()), expected)
            writes.append((path, data))
            path.write_bytes(data)
        prior = SimpleNamespace(
            atomic_file=atomic_file, IDENTITY=("pm_cwd", "args"),
            PM2_REMOVE="synthetic candidate-specific remove", PM2_ROOT=Path("/synthetic/pm2"),
            act_env=lambda: {}, POLICY={"autorestart": True},
        )
        obj = m.Release(prior)
        obj.work = record; obj.started = True; obj.reloaded = True
        obj.site = site; obj.original = b"original-route"
        obj.proposed = b"candidate-route"; obj.rollback_config = b"old-port-new-union"
        obj.original_dump = b"original-dump"; obj.new_dump = b"candidate-dump"
        obj.ids = [{"name": "retained-frontend", "pid": 123}]
        obj.current = {"pm2_env": {"env": dict(public_environment(), unique_id=OLD_PM2_ID)}}
        obj.public = public_environment()
        obj.guard = Mock(return_value=[])
        obj.command = Mock(return_value=b"")
        obj.verify_public = Mock()
        return obj, record, dump, writes

    def test_new_pm2_unique_id_is_not_inherited_or_compared_as_application_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, _, _ = self.fixture(directory)
            obj.current["pm2_env"]["env"].update({
                "unique_id": OLD_PM2_ID, "ACT_EXISTING_SETTING": "preserve-me",
                "PRIVATE_EXISTING_SETTING": "synthetic-private-value", "PORT": "3005",
            })
            retained = json.loads(json.dumps(obj.current))
            with patch.object(m, "RECORD", record):
                config = obj.candidate_config()
                self.assertNotIn("unique_id", config["env"])
                self.assertEqual(config["env"]["ACT_EXISTING_SETTING"], "preserve-me")
                self.assertEqual(config["env"]["PRIVATE_EXISTING_SETTING"], "synthetic-private-value")
                self.assertEqual(config["env"]["PORT"], str(m.PORT))
                self.assertEqual({key: config["env"][key] for key in obj.public}, obj.public)
                candidate = {"name": m.NAME, "pid": 456, "pm2_env": {
                    "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                    "exec_interpreter": config["interpreter"], "args": config["args"],
                    "env": dict(config["env"], unique_id=NEW_PM2_ID), "status": "online",
                }}
                obj.verify_candidate_row(candidate)
                obj.verify_candidate_row(candidate, healthy=False)
            self.assertEqual(obj.current, retained)

    def test_unique_id_exception_does_not_allow_application_or_ownership_environment_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, _, _ = self.fixture(directory)
            obj.current["pm2_env"]["env"].update({
                "unique_id": OLD_PM2_ID, "ACT_EXISTING_SETTING": "preserve-me",
                "PRIVATE_EXISTING_SETTING": "synthetic-private-value", "PORT": "3005",
            })
            with patch.object(m, "RECORD", record):
                config = obj.candidate_config()
                candidate = {"name": m.NAME, "pid": 456, "pm2_env": {
                    "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                    "exec_interpreter": config["interpreter"], "args": config["args"],
                    "env": dict(config["env"], unique_id=NEW_PM2_ID), "status": "online",
                }}
                # This exact baseline previously failed only because PM2 replaced unique_id.
                obj.verify_candidate_row(candidate)
                for key in config["env"]:
                    with self.subTest(environment_name=key):
                        changed = json.loads(json.dumps(candidate))
                        changed["pm2_env"]["env"][key] = "unexpected-value"
                        with self.assertRaises(m.Stop):
                            obj.verify_candidate_row(changed)

    def test_candidate_requires_a_new_canonical_pm2_uuid(self):
        invalid = (None, "", 123, {}, "not-a-uuid", OLD_PM2_ID,
                   "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
                   "22222222-2222-1222-8222-222222222222",
                   "22222222-2222-4222-7222-222222222222")
        for value in invalid:
            for healthy in (True, False):
                with self.subTest(value=value, healthy=healthy), tempfile.TemporaryDirectory() as directory:
                    obj, record, _, _ = self.fixture(directory)
                    with patch.object(m, "RECORD", record):
                        config = obj.candidate_config()
                        candidate = {"name": m.NAME, "pid": 456, "pm2_env": {
                            "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                            "exec_interpreter": config["interpreter"], "args": config["args"],
                            "env": dict(config["env"]), "status": "online",
                        }}
                        if value is not None:
                            candidate["pm2_env"]["env"]["unique_id"] = value
                        with self.assertRaises(m.Stop):
                            obj.verify_candidate_row(candidate, healthy=healthy)
                        self.assertFalse(hasattr(obj, "candidate_unique_id"))

    def test_first_accepted_candidate_id_is_pinned_for_launch_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, _, _ = self.fixture(directory)
            with patch.object(m, "RECORD", record):
                config = obj.candidate_config()
                candidate = {"name": m.NAME, "pid": 456, "pm2_env": {
                    "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                    "exec_interpreter": config["interpreter"], "args": config["args"],
                    "env": dict(config["env"], unique_id=NEW_PM2_ID), "status": "online",
                }}
                obj.verify_candidate_row(candidate)
                self.assertEqual(obj.candidate_unique_id, NEW_PM2_ID)
                obj.verify_candidate_row(candidate)
                changed = json.loads(json.dumps(candidate))
                changed["pm2_env"]["env"]["unique_id"] = OTHER_PM2_ID
                for healthy in (True, False):
                    with self.subTest(healthy=healthy), self.assertRaises(m.Stop):
                        obj.verify_candidate_row(changed, healthy=healthy)
                self.assertEqual(obj.candidate_unique_id, NEW_PM2_ID)

    def test_refused_configuration_does_not_pin_an_unaccepted_candidate_id(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, _, _ = self.fixture(directory)
            with patch.object(m, "RECORD", record):
                config = obj.candidate_config()
                refused = {"name": m.NAME, "pid": 456, "pm2_env": {
                    "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                    "exec_interpreter": config["interpreter"], "args": config["args"],
                    "env": dict(config["env"], unique_id=OTHER_PM2_ID), "status": "online",
                }}
                refused["pm2_env"]["env"]["ACT_TRACKING_ACTIVATION"] = "/unrelated/record"
                with self.assertRaises(m.Stop):
                    obj.verify_candidate_row(refused)
                self.assertFalse(hasattr(obj, "candidate_unique_id"))
                accepted = json.loads(json.dumps(refused))
                accepted["pm2_env"]["env"] = dict(config["env"], unique_id=NEW_PM2_ID)
                obj.verify_candidate_row(accepted)
                self.assertEqual(obj.candidate_unique_id, NEW_PM2_ID)

    def test_restores_only_owned_route_and_dump_retaining_asset_union(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, dump, writes = self.fixture(directory)
            with patch.object(m, "RECORD", record), patch.object(m, "DUMP", dump), patch.object(m, "emit"):
                obj.rollback()
            self.assertEqual(obj.site.read_bytes(), b"old-port-new-union")
            self.assertEqual(dump.read_bytes(), b"original-dump")
            self.assertEqual(writes, [(obj.site, b"old-port-new-union"), (dump, b"original-dump")])
            removals = [call for call in obj.command.call_args_list if call.args[0] == "candidate-remove"]
            self.assertEqual(len(removals), 1)
            payload = json.loads(removals[0].kwargs["data"])
            self.assertEqual(payload["name"], m.NAME)
            self.assertEqual(payload["activation_nonce"], str(record))
            self.assertEqual(payload["retained"], obj.ids)
            self.assertEqual(payload["cwd"], str(m.CANDIDATE))
            self.assertTrue(payload["allow_absent"])
            self.assertFalse(any("restart" in [str(arg) for arg in call.args[1]] for call in obj.command.call_args_list))
            obj.verify_public.assert_called_once_with(rollback=True)
            self.assertTrue((record / "PREVIOUS_FRONTEND_RESTORED.json").is_file())

    def test_unknown_live_route_is_preserved_before_any_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, dump, writes = self.fixture(directory)
            obj.site.write_bytes(b"another-release")
            with patch.object(m, "RECORD", record), patch.object(m, "DUMP", dump), self.assertRaisesRegex(m.Stop, "ROLLBACK_NGINX_UNKNOWN"):
                obj.rollback()
            self.assertEqual(writes, [])
            obj.command.assert_not_called()
            self.assertEqual(obj.site.read_bytes(), b"another-release")

    def test_unknown_saved_pm2_state_is_preserved_before_any_route_change(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, dump, writes = self.fixture(directory)
            dump.write_bytes(b"another-saved-state")
            with patch.object(m, "RECORD", record), patch.object(m, "DUMP", dump), self.assertRaisesRegex(m.Stop, "ROLLBACK_PM2_DUMP_UNKNOWN"):
                obj.rollback()
            self.assertEqual(writes, [])
            obj.command.assert_not_called()
            self.assertEqual(obj.site.read_bytes(), b"candidate-route")
            self.assertEqual(dump.read_bytes(), b"another-saved-state")

    def test_pre_switch_failed_start_keeps_original_routing_and_avoids_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, dump, writes = self.fixture(directory)
            obj.site.write_bytes(obj.original); dump.write_bytes(obj.original_dump)
            obj.reloaded = False
            with patch.object(m, "RECORD", record), patch.object(m, "DUMP", dump), patch.object(m, "emit"):
                obj.rollback()
            self.assertEqual(writes, [])
            self.assertEqual(obj.site.read_bytes(), obj.original)
            self.assertNotIn("rollback-nginx-reload", [call.args[0] for call in obj.command.call_args_list])
            obj.verify_public.assert_not_called()

    def test_completed_release_is_never_rolled_back_by_error_handler(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, dump, writes = self.fixture(directory)
            obj.complete = True
            with patch.object(m, "RECORD", record), patch.object(m, "DUMP", dump):
                obj.rollback()
            self.assertEqual(writes, [])
            obj.command.assert_not_called()

    def test_recovery_accepts_failed_owned_candidate_but_refuses_another_release(self):
        with tempfile.TemporaryDirectory() as directory:
            obj, record, dump, _ = self.fixture(directory)
            with patch.object(m, "RECORD", record):
                config = obj.candidate_config()
                env = {
                    "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                    "exec_interpreter": config["interpreter"], "args": config["args"],
                    "env": dict(config["env"], unique_id=NEW_PM2_ID), "status": "errored",
                }
                crashed = {"name": m.NAME, "pid": 0, "pm2_env": env}
                with self.assertRaises(m.Stop):
                    obj.verify_candidate_row(crashed)
                obj.verify_candidate_row(crashed, healthy=False)
                env["env"]["ACT_TRACKING_ACTIVATION"] = "/another/release-record"
                with self.assertRaises(m.Stop):
                    obj.verify_candidate_row(crashed, healthy=False)

    def test_actual_rollback_guard_allows_failed_candidate_without_relaxing_launch_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            obj, record, dump, _ = self.fixture(root)
            master = root / "nginx.conf"; master.write_bytes(b"master config")
            lock = root / "deploy.lock"; lock.write_bytes(b"")
            active = root / "active"; (active / ".next").mkdir(parents=True)
            (active / ".next/BUILD_ID").write_text("oldbuild")
            (active / "source.ts").write_text("old source")
            obj.master_hash = m.digest(master.read_bytes())
            obj.entries = sorted(obj.site.parent.iterdir())
            obj.other_nginx_hash = "retained-other-config"
            obj.other_nginx = Mock(return_value=obj.other_nginx_hash)
            obj.lock_identity = (lock.stat().st_dev, lock.stat().st_ino)
            obj.backend_baseline = {"pid": 101, "source": "retained"}
            obj.backend = Mock(return_value=obj.backend_baseline)
            obj.old_build = "oldbuild"; obj.source = m.source_tree(active)
            obj.assets_before = {"old.js": "retained asset hash"}
            obj.prior.tree = lambda path: obj.assets_before
            obj.prior.identity = lambda row: {"name": row["name"], "pid": row["pid"]}
            obj.prior.one = lambda rows, name: next(row for row in rows if row["name"] == name)
            old = {"name": "retained-frontend", "pid": 123, "pm2_env": {
                "env": dict(public_environment(), unique_id=OLD_PM2_ID)}}
            obj.current = old
            obj.public_environment = Mock(return_value=obj.public)
            # Exercise the real guard instead of the fixture's boundary stub.
            obj.guard = m.Release.guard.__get__(obj, m.Release)
            with patch.object(m, "RECORD", record), patch.object(m, "SITE", obj.site), \
                 patch.object(m, "MASTER", master), patch.object(m, "LOCK", lock), patch.object(m, "ACTIVE", active):
                config = obj.candidate_config()
                crashed = {"name": m.NAME, "pid": 0, "pm2_env": {
                    "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                    "exec_interpreter": config["interpreter"], "args": config["args"],
                    "env": dict(config["env"], unique_id=NEW_PM2_ID), "status": "errored",
                }}
                obj.rows = Mock(return_value=[old, crashed])
                self.assertEqual(obj.guard(obj.proposed, candidate=None), [old, crashed])
                with self.assertRaises(m.Stop):
                    obj.guard(obj.proposed, candidate=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
