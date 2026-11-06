"""Offline release-boundary tests. All host commands/PM2/HTTP use local fixtures."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import types
import unittest
from unittest import mock
from urllib.parse import urlsplit

SPEC = importlib.util.spec_from_file_location("passenger_frontend_release", Path(__file__).with_name("passenger_frontend_release.py"))
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
SOURCE_ROOT = Path(__file__).resolve().parents[2] / "act_website-main"


class Host:
    def __init__(self, root):
        self.root = root
        self.commands, self.rows, self.active_port = [], [], "3003"
        self.failure, self.backend_pid, self.other_config = None, 901, "unchanged"
        self.public = {"NEXT_PUBLIC_API_BASE_URL": release.ORIGIN, "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY": "offline-fixture"}
        self.source = {path: (SOURCE_ROOT / path).read_bytes() for path in release.ALLOWED}
        self.source.update({"package.json": b"{}\n", "package-lock.json": b"{}\n", "next.config.ts": b"export default {};\n"})
        for path in (release.BACKUP, release.SITE.parent, release.PM2_HOME, release.OLD_FRONT / ".next", release.OLD_ASSETS):
            path.mkdir(parents=True, mode=0o700, exist_ok=True)
        release.BACKUP.chmod(0o700)
        release.MASTER.write_text("pid /run/nginx.pid;\ninclude /etc/nginx/sites-enabled/*;\n")
        release.SITE.write_text("".join("location " + location + " {\n proxy_pass http://127.0.0.1:3003;\n}\n"
                                       for location in ("/", "/api/places", "/api/place-details"))
                                + "location /_next/static/ {\n alias " + str(release.OLD_ASSETS) + "/;\n}\n"
                                + "location /ws/ { proxy_pass http://unix:/run/act.sock; }\n")
        (release.OLD_FRONT / ".next/BUILD_ID").write_text("OLD_BUILD\n")
        (release.OLD_FRONT / ".env").write_text("PRIVATE_SYNTHETIC_VALUE=preserved\n")
        for relative, body in (("chunks/shared.js", b"shared-js"), ("css/shared.css", b"shared-css"), ("older.js", b"older-release")):
            path = release.OLD_ASSETS / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        for index, name in enumerate(release.RETAINED):
            cwd = release.OLD_FRONT if index == 2 else root / ("retained-" + str(index))
            cwd.mkdir(exist_ok=True)
            env = {"name": name, "pm_cwd": str(cwd), "pm_exec_path": str(cwd / "node_modules/next/dist/bin/next"),
                   "exec_interpreter": str(release.NODE), "args": release.ARGS[:-1] + [str(3001 + index)],
                   "exec_mode": "fork_mode", "env": {"OLD_PRIVATE_VALUE": "keep-" + str(index)},
                   **release.POLICY, "status": "online", "restart_time": 0, "pm_uptime": 100 + index}
            self.rows.append({"name": name, "pm_id": index, "pid": 1000 + index, "pm2_env": env})
        release.DUMP.write_bytes(release.encoded([copy.deepcopy(row["pm2_env"]) for row in self.rows]))
        self.original_site, self.original_dump = release.SITE.read_bytes(), release.DUMP.read_bytes()
        self.original_rows = copy.deepcopy(self.rows)

    def archive(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w") as archive:
            for path, body in self.source.items():
                member = tarfile.TarInfo("act_website-main/" + path)
                member.size, member.mode = len(body), 0o644
                archive.addfile(member, io.BytesIO(body))
        return output.getvalue()

    def html(self, new):
        build = "NEW_BUILD" if new else "OLD_BUILD"
        return ('<script src="/_next/static/chunks/shared.js"></script><link href="/_next/static/css/shared.css"/>'
                + '<script>build="' + build + '"</script>').encode()


class FixtureRelease(release.Release):
    host = None

    def backend(self):
        return {"pid": self.host.backend_pid, "pointer": "fixed-d77", "source": release.CONSUMER_HASH, "environment_hash": "unchanged"}

    def rows(self):
        self.daemon = 800
        return copy.deepcopy(self.host.rows)

    def other_nginx(self):
        return self.host.other_config

    def public_environment(self, rows):
        return copy.deepcopy(self.host.public)

    def capture_baseline(self):
        self.site, self.daemon = release.SITE, 800
        self.public = self.public_environment(self.rows())
        self.baseline = {"backend": self.backend(), "retained": [release.identity(row) for row in self.host.original_rows],
            "daemon": self.daemon, "dump_hash": release.sha(release.regular(release.DUMP)),
            "master_hash": release.sha(release.regular(release.MASTER)), "entries": [str(release.SITE)],
            "other_nginx_hash": self.other_nginx(), "old_site_hash": release.sha(release.regular(self.site)),
            "old_build_id": "OLD_BUILD", "prior_plan_hash": "pinned", "prior_receipt_hash": "pinned",
            "env_hashes": {".env": release.sha(release.regular(release.OLD_FRONT / ".env"))}}
        self.retained(self.rows())

    def git(self, *args):
        if args[:2] == ("remote", "get-url"):
            return b"git@github.com:mahmood1990farhat-hub/act-website-automation.git\n"
        if args[0] in ("fetch", "merge-base"):
            return b""
        if args[0] == "rev-parse":
            return (release.REVIEWED_SHA + "\n").encode()
        if args[0] == "diff":
            if "--diff-filter=D" in args:
                return b""
            return "\n".join("act_website-main/" + path for path in sorted(release.ALLOWED)).encode()
        if args[0] == "show":
            return self.host.source[args[1].split(":act_website-main/", 1)[1]]
        if args[0] == "archive":
            return self.host.archive()
        raise AssertionError("Unexpected Git action")

    def command(self, label, args, **kwargs):
        self.host.commands.append(label)
        if label in ("candidate-port", "npm-ci") or label.startswith("nginx-validate-"):
            return b""
        if label == "frontend-build":
            build = self.front / ".next"
            (build / "static/chunks").mkdir(parents=True)
            (build / "static/css").mkdir()
            (build / "BUILD_ID").write_text("NEW_BUILD\n")
            (build / "static/chunks/shared.js").write_bytes(b"shared-js")
            (build / "static/css/shared.css").write_bytes(b"shared-css")
            (build / "static/chunks/passenger-new.js").write_bytes(b"new-passenger-render")
            return b""
        if label == "pm2-start-candidate":
            payload = json.loads(kwargs["data"])
            if self.host.failure != "unconfirmed_absent":
                config = payload["config"]
                env = {"name": config["name"], "pm_cwd": config["cwd"], "pm_exec_path": config["script"],
                       "exec_interpreter": config["interpreter"], "args": config["args"], "exec_mode": "fork_mode",
                       "env": config["env"], **release.POLICY, "status": "online", "restart_time": 0, "pm_uptime": 999}
                self.host.rows.append({"name": config["name"], "pm_id": 3, "pid": 2000, "pm2_env": env})
            if self.host.failure in ("partial_start", "unconfirmed_absent"):
                raise release.Stop("Simulated incomplete startup")
            return b""
        if label == "remove-only-candidate":
            payload = json.loads(kwargs["data"])
            found = [row for row in self.host.rows if row["name"] == payload["name"]]
            if not found:
                release.require(payload["allow_absent"], "Unacknowledged candidate start remains uncertain.")
            else:
                release.require(len(found) == 1 and found[0]["pm2_env"]["env"]["ACT_TRACKING_ACTIVATION"] == payload["activation_nonce"], "Candidate ownership differs.")
                self.host.rows.remove(found[0])
            return b""
        if label.startswith("nginx-"):
            if label in ("nginx-reload", "nginx-rollback-reload"):
                self.host.active_port = "3004" if b"127.0.0.1:3004" in release.SITE.read_bytes() else "3003"
            return b""
        if label == "frontend-integrity":
            url = urlsplit(str(args[-1]))
            port = str(url.port) if url.port else self.host.active_port
            if url.path == "/en":
                new = port == "3004"
                if not url.port and self.host.failure == "wrong_public_build" and new:
                    new = False
                return self.host.html(new) + b"\n200"
            relative = url.path.removeprefix("/_next/static/")
            assets = self.assets if b"127.0.0.1:3004" in release.SITE.read_bytes() or self.reload_attempted else release.OLD_ASSETS
            return (assets / relative).read_bytes() + b"\n200"
        raise AssertionError("Unexpected host command: " + label)


class PassengerReleaseTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        front = root / "front"
        self.stack.enter_context(mock.patch.multiple(release, FRONT_ROOT=front, OLD_FRONT=front / "releases/old3a",
            OLD_ASSETS=front / "old-assets", BACKUP=root / "private", SITE=root / "nginx/sites-enabled/act",
            MASTER=root / "nginx/nginx.conf", PM2_HOME=root / "pm2", DUMP=root / "pm2/dump.pm2"))
        self.stack.enter_context(mock.patch.object(release.pwd, "getpwnam", return_value=types.SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())))
        # Private-path permission semantics are tested on the caller-owned temp tree.
        self.stack.enter_context(mock.patch.object(release, "private", side_effect=lambda path: self.assertFalse(path.is_symlink())))
        self.host = Host(root)
        FixtureRelease.host = self.host
        original_resolve = Path.resolve
        def resolve(path, *args, **kwargs):
            if str(path).startswith("/proc/") and path.name == "cwd":
                pid = int(path.parent.name)
                return Path(next(row["pm2_env"]["pm_cwd"] for row in self.host.rows if row["pid"] == pid))
            return original_resolve(path, *args, **kwargs)
        self.stack.enter_context(mock.patch.object(Path, "resolve", resolve))
        self.output = self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def prepared(self):
        operation = FixtureRelease(release.REVIEWED_SHA)
        operation.prepare()
        return operation.record

    def activation(self):
        operation = FixtureRelease(release.REVIEWED_SHA, self.prepared())
        operation.preflight()
        return operation

    def test_exact_reviewed_sha_paths_and_content_are_required(self):
        operation = FixtureRelease(release.REVIEWED_SHA)
        operation.require_source()
        operation.revision = "1" * 40
        with self.assertRaises(release.Stop):
            operation.require_source()
        operation.revision = release.REVIEWED_SHA
        self.host.source[next(iter(release.REVIEWED_FILES))] = b"unreviewed"
        with self.assertRaises(release.Stop):
            operation.require_source()
        with mock.patch.object(release, "Release") as constructor:
            with self.assertRaises(release.Stop):
                release.main(["--prepare", "--frontend-sha", "1" * 40])
            constructor.assert_not_called()

    def test_preparation_builds_once_without_changing_live_state(self):
        record = self.prepared()
        plan = json.loads((record / "plan.json").read_bytes())
        self.assertEqual(plan["state"], "PREPARED_NOT_ACTIVE")
        self.assertEqual(self.host.commands.count("frontend-build"), 1)
        self.assertEqual(self.host.commands.count("npm-ci"), 1)
        self.assertFalse(any(label.startswith("pm2-") or label == "nginx-reload" for label in self.host.commands))
        self.assertEqual(release.SITE.read_bytes(), self.host.original_site)
        self.assertEqual(release.DUMP.read_bytes(), self.host.original_dump)
        self.assertEqual(self.host.rows, self.host.original_rows)
        self.assertNotIn("PRIVATE_SYNTHETIC_VALUE", self.output.getvalue())

    def test_route_scope_and_complete_asset_union_are_enforced(self):
        original = release.SITE.read_bytes()
        candidate, rollback = release.route_pair(original, self.host.root / "combined")
        self.assertEqual(candidate.count(b"127.0.0.1:3004"), 3)
        self.assertEqual(rollback.count(b"127.0.0.1:3003"), 3)
        self.assertIn(b"proxy_pass http://unix:/run/act.sock", candidate)
        with self.assertRaises(release.Stop):
            release.route_pair(original + b"proxy_pass http://127.0.0.1:3003;\n", self.host.root / "bad")
        newer = self.host.root / "new-assets"
        (newer / "deep/nested").mkdir(parents=True)
        (newer / "deep/nested/new.js").write_bytes(b"new")
        destination = self.host.root / "combined"
        before = os.umask(0o077)
        try:
            manifest = release.copy_assets((release.OLD_ASSETS, newer), destination)
        finally:
            os.umask(before)
        self.assertIn("older.js", manifest)
        self.assertIn("deep/nested/new.js", manifest)
        self.assertTrue(all(Path(current).stat().st_mode & 0o777 == 0o755 for current, _, _ in os.walk(destination)))
        (newer / "older.js").write_bytes(b"different")
        with self.assertRaises(release.Stop):
            release.copy_assets((release.OLD_ASSETS, newer), self.host.root / "collision")

    def test_preflight_rejects_candidate_environment_and_source_drift(self):
        record = self.prepared()
        plan = json.loads((record / "plan.json").read_bytes())
        front = Path(plan["front"])
        old = (front / ".env").read_bytes()
        (front / ".env").write_bytes(b"changed")
        with self.assertRaises(release.Stop):
            FixtureRelease(release.REVIEWED_SHA, record).preflight()
        (front / ".env").write_bytes(old)
        (front / ".env.local").write_bytes(b"extra")
        with self.assertRaises(release.Stop):
            FixtureRelease(release.REVIEWED_SHA, record).preflight()
        (front / ".env.local").unlink()
        source = front / "src/components/_components/Trips/MyTripsCard.tsx"
        source.write_bytes(b"changed after build")
        with self.assertRaises(release.Stop):
            FixtureRelease(release.REVIEWED_SHA, record).preflight()
        self.assertFalse(any(label.startswith("pm2-") for label in self.host.commands))

    def test_success_preserves_all_three_definitions_and_verifies_build_identity(self):
        operation = self.activation()
        operation.activate()
        self.assertTrue(operation.complete)
        self.assertEqual(self.host.active_port, "3004")
        self.assertEqual(self.host.rows[:3], self.host.original_rows)
        self.assertEqual(json.loads(release.DUMP.read_bytes())[:3], json.loads(self.host.original_dump))
        self.assertEqual(operation.old_paths, operation.new_paths)  # Deliberately needs BUILD_ID discrimination.
        self.assertEqual(self.host.backend_pid, 901)
        self.assertTrue((operation.work / "ACTIVATED.json").is_file())

    def test_wrong_public_build_rolls_back_to_3a_and_preserves_union(self):
        operation = self.activation()
        self.host.failure = "wrong_public_build"
        with self.assertRaisesRegex(release.Stop, "wrong frontend build ID"):
            operation.activate()
        operation.recover()
        self.assertEqual(self.host.active_port, "3003")
        self.assertEqual(release.SITE.read_bytes(), operation.rollback)
        self.assertIn(str(operation.assets).encode(), release.SITE.read_bytes())
        self.assertEqual(release.DUMP.read_bytes(), self.host.original_dump)
        self.assertEqual(self.host.rows, self.host.original_rows)
        self.assertEqual(self.host.backend_pid, 901)
        self.assertTrue((operation.work / "FRONTEND_ROLLED_BACK.json").is_file())

    def test_partial_start_cleanup_is_owned_and_absent_unacknowledged_start_is_not_claimed_clean(self):
        operation = self.activation()
        self.host.failure = "partial_start"
        with self.assertRaises(release.Stop):
            operation.activate()
        self.assertFalse(operation.start_acknowledged)
        operation.recover()
        self.assertEqual(self.host.rows, self.host.original_rows)
        self.assertEqual(release.SITE.read_bytes(), self.host.original_site)
        self.assertEqual(release.DUMP.read_bytes(), self.host.original_dump)
        operation.work = operation.record / "uncertain-activation"
        operation.work.mkdir()
        operation.start_attempted = False
        self.host.failure = "unconfirmed_absent"
        with self.assertRaises(release.Stop):
            operation.activate()
        with self.assertRaisesRegex(release.Stop, "remains uncertain"):
            operation.recover()
        self.assertFalse((operation.work / "FRONTEND_ROLLED_BACK.json").exists())

    def test_concurrent_site_or_backend_change_withholds_automatic_overwrite(self):
        operation = self.activation()
        self.host.failure = "partial_start"
        with self.assertRaises(release.Stop):
            operation.activate()
        edited = release.SITE.read_bytes() + b"# concurrent operator change\n"
        release.SITE.write_bytes(edited)
        with self.assertRaisesRegex(release.Stop, "Concurrent routing edit"):
            operation.recover()
        self.assertEqual(release.SITE.read_bytes(), edited)
        self.assertNotIn("remove-only-candidate", self.host.commands)
        release.SITE.write_bytes(self.host.original_site)
        self.host.backend_pid += 1
        with self.assertRaisesRegex(release.Stop, "Backend identity changed"):
            operation.recover()


if __name__ == "__main__":
    unittest.main()
