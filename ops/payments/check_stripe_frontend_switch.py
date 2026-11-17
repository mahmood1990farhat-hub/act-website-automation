#!/usr/bin/env python3
"""ACT Stripe frontend switch preflight: READ-ONLY, no activation command.

Check current accepted PM2/Nginx/source against the validated inactive build.
Uses existing pinned verification and prior reviewed release read primitives.
Does not start a process, create a plan, alter config or perform payments.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

VERIFY = Path("/root/act-stripe-readonly/verify_stripe_frontend_candidate.py")
VERIFY_HASH = "dc2821f79a84f122f3c27d672aec685eff2634e3302c01072da8cedbefe63859"
PREVIOUS = Path("/root/act-stripe-readonly/passenger_frontend_release.py")
PREVIOUS_HASH = "2c880f9e116dad51b5acf973f49b992dbe8c8af4fca1883bd8f718b440151254"
SITE = Path("/etc/nginx/sites-enabled/airportandcitytransfer")
EXPECTED_NAMES = frozenset({
    "act", "act-preview-892317f", "act-tracking-3a82c16",
    "act-passenger-02e59f9",
})
OLD_PORT = 3004
NEW_PORT = 3005


class Stop(Exception):
    """May contain only fixed, non-secret error codes."""


def require(ok, code):
    if not ok:
        raise Stop(code)


def hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def load_pinned(path, expected, name):
    require(path.is_file() and not path.is_symlink(), "PINNED_HELPER_NOT_REGULAR")
    require(hash_bytes(path.read_bytes()) == expected, "PINNED_HELPER_HASH_CHANGED")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "PINNED_HELPER_UNAVAILABLE")
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def propose_config(original, old_assets, new_assets):
    """Only three proxy endpoints and a single static alias may change."""
    text = original.decode("utf-8")
    upstream = re.compile(r"(?m)^([ \t]*proxy_pass[ \t]+)http://127\.0\.0\.1:3004([ \t]*;)")
    alias = re.compile(r"(?m)^([ \t]*alias[ \t]+)" + re.escape(str(old_assets)) + r"/([ \t]*;)")
    require(len(upstream.findall(text)) == 3, "EXPECTED_THREE_OLD_FRONTEND_UPSTREAMS")
    require(len(alias.findall(text)) == 1, "EXPECTED_ONE_OLD_STATIC_ALIAS")
    changed = upstream.sub(lambda m: m[1] + "http://127.0.0.1:3005" + m[2], text)
    changed = alias.sub(lambda m: m[1] + str(new_assets) + "/" + m[2], changed)
    require(changed != text and len(re.findall(
        r"(?m)^[ \t]*proxy_pass[ \t]+http://127\.0\.0\.1:3005[ \t]*;", changed)) == 3,
        "PROPOSED_FRONTEND_ROUTES_INVALID")
    require(changed.count(str(new_assets) + "/") == 1,
            "PROPOSED_STATIC_ALIAS_INVALID")
    # A successful inverse must reproduce the exact old file, byte for byte.
    inverse = changed.replace("http://127.0.0.1:3005", "http://127.0.0.1:3004")
    inverse = inverse.replace(str(new_assets) + "/", str(old_assets) + "/")
    require(inverse == text, "NGINX_ROLLBACK_NOT_EXACT")
    return changed.encode("utf-8")


def run(args, *, env=None):
    try:
        result = subprocess.run([str(x) for x in args], env=env,
                                capture_output=True, timeout=25)
    except (OSError, subprocess.TimeoutExpired):
        raise Stop("READ_ONLY_COMMAND_UNAVAILABLE") from None
    require(result.returncode == 0, "READ_ONLY_COMMAND_FAILED")
    return result.stdout


def check_pm2(previous, stage):
    require((previous.PM2_HOME / "rpc.sock").is_socket(),
            "PM2_EXISTING_SOCKET_MISSING")
    daemon = int((previous.PM2_HOME / "pm2.pid").read_bytes().strip())
    require(daemon > 1, "PM2_DAEMON_INVALID")
    os.kill(daemon, 0)
    rows = json.loads(run([
        "/usr/sbin/runuser", "-u", "act", "--",
        previous.NODE, "-e", previous.PM2_READ,
        previous.PM2_ROOT, previous.PM2_HOME / "rpc.sock"
    ], env=previous.act_env()))
    saved = json.loads((previous.DUMP).read_bytes())
    require(isinstance(rows, list) and len(rows) == 4 and
            {item.get("name") for item in rows} == EXPECTED_NAMES,
            "CURRENT_PM2_INVENTORY_DRIFT")
    require(isinstance(saved, list) and len(saved) == 4 and
            {item.get("name") for item in saved} == EXPECTED_NAMES,
            "SAVED_PM2_INVENTORY_DRIFT")
    for item in rows:
        values = item.get("pm2_env") or {}
        require(item.get("pid", 0) > 1 and values.get("status") == "online",
                "PM2_EXPECTED_PROCESS_NOT_ONLINE")
        stored = next(entry for entry in saved if entry["name"] == item["name"])
        require(all(stored.get(key) == values.get(key) for key in previous.LAUNCH),
                "PM2_SAVED_LAUNCH_DRIFT")
        if item["name"] == "act-passenger-02e59f9":
            require(values.get("pm_cwd") == str(stage.ACTIVE) and
                    Path(f"/proc/{item['pid']}/cwd").resolve(strict=True) == stage.ACTIVE,
                    "PM2_CURRENT_FRONTEND_DRIFT")
    return True


def check():
    require(os.geteuid() == 0, "ROOT_READ_ONLY_REQUIRED")
    verifier = load_pinned(VERIFY, VERIFY_HASH, "act_stripe_candidate_verifier_pinned")
    previous = load_pinned(PREVIOUS, PREVIOUS_HASH, "act_previous_release_helper_pinned")
    stage = verifier.import_pinned_helper()
    baseline = stage.local_state()
    plan = verifier.private_plan(stage.RECORD / "plan.json")
    verifier.validate_plan(stage, plan, baseline)
    verifier.validate_candidate(stage, plan, baseline)
    require(SITE.is_symlink(), "NGINX_SITE_LINK_CHANGED")
    site = SITE.resolve(strict=True)
    require(site.is_relative_to(Path("/etc/nginx")) and site.is_file() and not site.is_symlink(),
            "NGINX_SITE_OUTSIDE_EXPECTED_ROOT")
    original = site.read_bytes()
    require(hash_bytes(original) == baseline["nginx_sha256"],
            "NGINX_LIVE_SITE_DRIFT")
    proposed = propose_config(original, stage.OLD_ASSETS, stage.NEW_ASSETS)
    require(hash_bytes(proposed) != hash_bytes(original), "NGINX_SWITCH_NOT_NEEDED")
    require(not run(["/usr/bin/ss", "-H", "-ltn", f"sport = :{NEW_PORT}"]).strip(),
            "NEW_FRONTEND_PORT_ALREADY_USED")
    check_pm2(previous, stage)
    return True


def main():
    try:
        check()
        print("PASS: PROPOSED_THREE_UPSTREAM_AND_ONE_ASSET_ALIAS_SWITCH")
        print("PASS: EXACT_NGINX_ROLLBACK_PREIMAGE")
        print("PASS: CURRENT_AND_SAVED_PM2_PROCESSES_PRESERVED")
        print("PASS: NEW_FRONTEND_PORT_UNUSED")
        print("PASS: STAGED_STRIPE_FRONTEND_STILL_VERIFIED")
        print("NO_CHANGES; NO_ACTIVATION_COMMAND")
        return 0
    except Stop as exc:
        print("STOPPED: " + str(exc) + "; NO_CHANGES", file=sys.stderr)
        return 1
    except Exception:
        print("STOPPED: FRONTEND_SWITCH_PREFLIGHT_UNAVAILABLE; NO_CHANGES",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
