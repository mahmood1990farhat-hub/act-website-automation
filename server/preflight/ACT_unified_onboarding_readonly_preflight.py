#!/usr/bin/env python3
"""ACT unified driver onboarding: READ-ONLY production preflight.

Run locally on the ACT Debian host with sufficient read permissions, e.g.
  sudo python3 ACT_unified_onboarding_readonly_preflight.py

No database writes, migrations, backups, deployments, service restarts,
secret printing, file creation or network calls are performed.
The result is diagnostic evidence, NOT approval to deploy.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys

PRODUCTION_BACKEND_SHA = "dc1df73122aafba9d818f9059cd11c17a621405c"
PRODUCTION_FRONTEND_SHA = "4ef5418408cbd3ef7f1027763963aca4ed02354e"
CANDIDATE_BACKEND_SHA = "c02fa3c5520c7d0e00f8d8d9653471d726d58bac"
CANDIDATE_FRONTEND_SHA = "6c6aca306961ad9750ba81df8fefc9411dc5a24e"
DEPLOY_HELPER_BLOB = "4df289fbff83f638b49f1711926b39c23ad29e08"
BACKEND_LINK = Path("/var/www/atg/atg-backend/current")
SHARED_DIR = Path("/var/www/atg/atg-backend/shared")
FRONTEND_DIR = Path("/var/www/atg/front-end/airportandcitytransfer")
FRONTEND_REPO = Path("/var/www/atg/front-end/airportandcitytransfer_repo")
DEPLOY_HELPER = Path("/usr/local/sbin/act-backend-deploy")
SKIP_DIRS = {".git", ".next", "node_modules", ".turbo"}
SKIP_FILES = {".env", "next-env.d.ts"}
findings = []


def result(name, status, detail):
    assert status in ("PASS", "HOLD", "MANUAL")
    findings.append((name, status, detail))
    print(f"{status:6} {name}: {detail}")


def safe_run(args, *, cwd=None, timeout=35):
    try:
        proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def read_env_key(path, key):
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    found = None
    for line in content.splitlines():
        match = re.match(r"\s*(?:export\s+)?" + re.escape(key) + r"\s*=\s*(.*)$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        found = value
    return found


def within(path, parent):
    try:
        p, q = os.path.realpath(str(path)), os.path.realpath(str(parent))
        return os.path.commonpath((p, q)) == q
    except (ValueError, OSError):
        return False


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def backend_checks():
    print("\n--- Accepted live backend and deploy helper ---")
    if not BACKEND_LINK.exists():
        result("backend_current", "HOLD", "current backend link/directory not found")
        return
    try:
        doc = json.loads((BACKEND_LINK / "release.json").read_text(encoding="utf-8"))
        seen = doc.get("git_sha", "")
    except (OSError, json.JSONDecodeError):
        seen = ""
    if seen == PRODUCTION_BACKEND_SHA:
        result("backend_current", "PASS", "accepted backend SHA matches release.json")
    else:
        result("backend_current", "HOLD", "live release.json missing or not accepted backend SHA")
    if not DEPLOY_HELPER.is_file():
        result("backend_deploy_helper", "HOLD", "installed deployment helper unavailable")
    else:
        try:
            match = git_blob(DEPLOY_HELPER.read_bytes()) == DEPLOY_HELPER_BLOB
        except OSError:
            match = False
        result("backend_deploy_helper", "PASS" if match else "HOLD",
               "installed helper matches reviewed GitHub blob" if match else "installed helper differs or unreadable: review before deployment")
    result("migration_recovery", "MANUAL", "current script does NOT auto-rollback after applied migrations; forward recovery or approved DB restore needed")


def private_storage_checks():
    print("\n--- Private persistent driver evidence ---")
    env_path = SHARED_DIR / ".env"
    root = read_env_key(env_path, "ACT_DRIVER_PRIVATE_UPLOAD_ROOT")
    if not root or not root.startswith("/") or "$" in root:
        result("private_root_config", "HOLD", "unset, unreadable or nonabsolute ACT_DRIVER_PRIVATE_UPLOAD_ROOT in shared .env (value not shown)")
        return
    p = Path(root)
    if not p.is_dir():
        result("private_root_config", "HOLD", "configured path is not an existing persistent directory")
        return
    result("private_root_config", "PASS", "private root is configured and exists (path redacted)")
    exposed_roots = [SHARED_DIR / "media", SHARED_DIR / "static", BACKEND_LINK / "media",
                     BACKEND_LINK / "static", FRONTEND_DIR]
    if any(within(p, public) for public in exposed_roots):
        result("private_root_public_separation", "HOLD", "private root overlaps known public media/static/frontend location")
    else:
        result("private_root_public_separation", "PASS", "outside known ACT media/static/frontend paths")
    try:
        details = p.stat()
        mode = stat.S_IMODE(details.st_mode)
        uid = pwd.getpwnam("www-data").pw_uid
        good = details.st_uid == uid and (mode & 0o077) == 0 and (mode & 0o700) == 0o700
    except (OSError, KeyError):
        good = False
    result("private_root_permissions", "PASS" if good else "HOLD",
           "www-data owns root with user-only 0700 permissions" if good else "owner/mode is not expected www-data 0700; inspect without changing")
    if shutil.which("runuser"):
        rc, _ = safe_run(["runuser", "-u", "www-data", "--", "test", "-w", str(p)])
        rx, _ = safe_run(["runuser", "-u", "www-data", "--", "test", "-x", str(p)])
        result("private_root_app_access", "PASS" if rc == 0 and rx == 0 else "HOLD",
               "www-data can traverse and write" if rc == 0 and rx == 0 else "www-data write/traversal cannot be confirmed")
    else:
        result("private_root_app_access", "MANUAL", "runuser unavailable; independently verify www-data access")
    # Parse Nginx's effective config *without printing it*; nonliteral aliases
    # and bespoke rewrites require human review even if this simple check passes.
    if shutil.which("nginx"):
        rc, out = safe_run(["nginx", "-T"], timeout=35)
        if rc != 0:
            result("nginx_alias_exposure", "HOLD", "cannot inspect effective Nginx configuration")
        else:
            locations = re.findall(r"^\s*(?:root|alias)\s+([^;]+);", out, flags=re.MULTILINE)
            literal = [s.strip().strip("\"'") for s in locations if "$" not in s]
            possible = [s for s in literal if s.startswith("/") and within(p, s)]
            if possible:
                result("nginx_alias_exposure", "HOLD", "private root lies inside an Nginx root/alias")
            elif not locations:
                result("nginx_alias_exposure", "MANUAL", "no paths parsed; independently inspect site Nginx rules")
            else:
                result("nginx_alias_exposure", "PASS", "no direct literal Nginx alias/root overlap found")
    else:
        result("nginx_alias_exposure", "MANUAL", "Nginx unavailable; host config must be inspected")
    result("nginx_full_security_review", "MANUAL", "review dynamic aliases, rewrites and symlinks; scripted path scan is not a security sign-off")
    result("driver_document_policy", "MANUAL", "agree category-specific retention, secure disposal and restricted off-host backup/restore")
    result("tfl_operator_records", "MANUAL", "verify NI number, registered keeper details, driver/vehicle availability dates and record retention BEFORE allowing dispatch; these fields are not established by scoped PR #94")


def migration_backup_checks():
    print("\n--- Database migration and backup gates ---")
    backup_path = SHARED_DIR / "backups"
    if backup_path.is_dir():
        try:
            m = stat.S_IMODE(backup_path.stat().st_mode)
            secure = (m & 0o007) == 0
            result("backup_root", "PASS" if secure else "HOLD",
                   "persistent backup directory exists; no access for others" if secure else "backup directory permits 'others' access")
        except OSError:
            result("backup_root", "HOLD", "backup directory unreadable")
    else:
        result("backup_root", "HOLD", "expected shared backup directory does not exist")
    available = all(shutil.which(command) for command in ("pg_dump", "pg_restore"))
    result("postgres_tools", "PASS" if available else "HOLD", "pg_dump and pg_restore available" if available else "missing pg_dump/pg_restore")
    python = BACKEND_LINK / ".venv/bin/python"
    # A SELECT through Django uses the live DB only for a read-only inspection.
    cmd = "import json; from django.db import connection; c=connection.cursor(); c.execute(\"SELECT name FROM django_migrations WHERE app = 'drivers' ORDER BY name\"); print('ACT_DRIVER_MIGRATIONS=' + json.dumps([r[0] for r in c.fetchall()]))"
    if python.exists() and shutil.which("runuser"):
        rc, output = safe_run(["runuser", "-u", "www-data", "--", str(python), "-B", "manage.py", "shell", "-c", cmd], cwd=BACKEND_LINK, timeout=35)
        data = re.findall(r"^ACT_DRIVER_MIGRATIONS=(.*)$", output, re.MULTILINE)
        if rc == 0 and data:
            try:
                migrations = json.loads(data[-1]); names = set(migrations)
                baseline_names = {"0001_initial", "0002_professional_vehicle_labels", "0003_passenger_driver_details"}
                good = names == baseline_names
                result("migration_state", "PASS" if good else "HOLD",
                       "exact expected production driver migrations 0001-0003 applied; no extra driver migrations" if good else "driver migration state differs from expected production baseline")
            except json.JSONDecodeError:
                result("migration_state", "HOLD", "Django migration query returned unreadable result")
        else:
            result("migration_state", "HOLD", "could not read live django_migrations; check DB access privately")
    else:
        result("migration_state", "HOLD", "backend Python or read-only DB query unavailable")
    result("pre_migration_backup", "MANUAL", "owner must approve fresh backup, checksum, off-host copy and real disposable-DB restore before applying 0004/0005")
    result("migration_plan", "MANUAL", "review exact live migrate --plan; stop if pending migrations other than approved 0004/0005")


def frontend_checks():
    print("\n--- Live frontend drift from accepted SHA ---")
    if not FRONTEND_DIR.is_dir() or not FRONTEND_REPO.is_dir():
        result("frontend_source", "HOLD", "frontend live directory or local Git checkout is missing")
        return
    rc, out = safe_run(["git", "-C", str(FRONTEND_REPO), "cat-file", "-t", PRODUCTION_FRONTEND_SHA])
    if rc != 0 or out.strip() != "commit":
        result("frontend_source", "HOLD", "accepted SHA unavailable in local Git objects; no git fetch was attempted")
        return
    proc = subprocess.run(["git", "-C", str(FRONTEND_REPO), "ls-tree", "-rz", PRODUCTION_FRONTEND_SHA, "--", "act_website-main/"], capture_output=True, check=False)
    if proc.returncode != 0:
        result("frontend_source", "HOLD", "could not read Git tree for accepted frontend")
        return
    expected = {}
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        try:
            meta, path = record.split(b"\t", 1)
            mode, typ, blob = meta.split(b" ", 2)
            if typ != b"blob":
                continue
            name = path.decode("utf-8").removeprefix("act_website-main/")
            parts = Path(name).parts
            if any(p in SKIP_DIRS for p in parts) or Path(name).name in SKIP_FILES:
                continue
            expected[name] = blob.decode("ascii")
        except (ValueError, UnicodeDecodeError):
            result("frontend_git_tree", "HOLD", "unrecognised Git tree entry")
            return
    changes = []
    for rel, blob in expected.items():
        live = FRONTEND_DIR / rel
        if not live.is_file():
            changes.append("missing:" + rel)
        else:
            try:
                if git_blob(live.read_bytes()) != blob:
                    changes.append("modified:" + rel)
            except OSError:
                changes.append("unreadable:" + rel)
    extra = []
    for root, dirs, filenames in os.walk(FRONTEND_DIR, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (Path(root) / d).is_symlink()]
        for filename in filenames:
            if filename in SKIP_FILES:
                continue
            rel = str((Path(root) / filename).relative_to(FRONTEND_DIR))
            if rel not in expected:
                extra.append("extra:" + rel)
    changes.extend(extra)
    result("frontend_drift", "PASS" if not changes else "HOLD",
           "live tracked source exactly matches accepted SHA (excluded env/build dependencies)" if not changes
           else f"{len(changes)} differences; examples: " + ", ".join(changes[:8]))
    result("frontend_activation", "MANUAL", "existing workflow is pinned to an older SHA; independent guarded release and rollback required")


def main():
    print("ACT UNIFIED DRIVER - READ-ONLY PRE-RELEASE PREFLIGHT")
    print("Accepted backend:", PRODUCTION_BACKEND_SHA)
    print("Accepted frontend:", PRODUCTION_FRONTEND_SHA)
    print("Proposed backend:", CANDIDATE_BACKEND_SHA)
    print("Proposed frontend:", CANDIDATE_FRONTEND_SHA)
    print("NO DEPLOYMENT / MIGRATIONS / BACKUP CREATION / N8N CHANGES")
    if os.geteuid() != 0:
        result("read_permissions", "MANUAL", "run as root for complete non-mutating host inspection; no secret content is printed")
    backend_checks()
    private_storage_checks()
    migration_backup_checks()
    frontend_checks()
    print("\n--- Final ---")
    for status in ("PASS", "HOLD", "MANUAL"):
        print(f"{status}: {sum(1 for _, s, _ in findings if s == status)}")
    print("RESULT: RELEASE NOT AUTHORISED. Owner sign-off and manual gates are mandatory.")
    return 2 if any(s == "HOLD" for _, s, _ in findings) else 3  # Manual gates remain; never signal deployment readiness


if __name__ == "__main__":
    sys.exit(main())