#!/usr/bin/env python3
"""Replace only ACT's expired Stripe TEST secret; no key is accepted in argv.

Default/--check is read-only. --apply requires a root terminal, validates the
replacement with Stripe GETs, keeps a private backup, then restarts act.service
once. A restart/readiness failure retains the new config and backup for review;
it never silently restores the known-expired key or restarts another service.
"""
import argparse
import fcntl
import getpass
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shlex
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import warnings
from dataclasses import dataclass

SERVICE = "act.service"
CURRENT = Path("/var/www/atg/atg-backend/current")
ENV_FILE = Path("/var/www/atg/atg-backend/shared/.env")
BACKUP_ROOT = Path("/root/act-release-backup")
LOCK_FILE = Path("/run/lock/act-backend-deploy.lock")
SOCKET = "/run/act.sock"
ACCOUNT = "acct_1RDnQjBxjYEaMc5N"
BACKEND_SHA = "d77e896af9daca5a39b7a85d5b76c5821e008d23"
CONSUMER_SHA256 = "d10d943b079041e0998daae2e4ece3a90c1b125f64107ef4676c1d51d9c55bed"
KEY_LINE = re.compile(rb"(?m)^[ \t]*(?:export[ \t]+)?STRIPE_SECRET_KEY[ \t]*=[ \t]*([^\r\n]*)")
KEY_VALUE = re.compile(rb"(?:(['\"])(sk_test_[A-Za-z0-9]{16,240})\1|(sk_test_[A-Za-z0-9]{16,240}))([ \t]*(?:#.*)?)\Z")
MUTATION_STAGE = "UNCHANGED"


class Refusal(Exception):
    """Only fixed, non-secret reason codes are allowed in this exception."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error embeds argv, which could contain a pasted key.
        raise Refusal("INVALID_ARGUMENTS_USE_CHECK_OR_APPLY_WITHOUT_KEY")


def require(condition, code):
    if not condition:
        raise Refusal(code)


def command(argv, timeout=5):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0, "SERVICE_QUERY_FAILED")
    return result.stdout.strip()


@dataclass
class FileSnapshot:
    data: bytes
    identity: tuple
    uid: int
    gid: int
    mode: int


def root_directory(path):
    info = path.stat()
    require(path.resolve(strict=True) == path and info.st_uid == 0
            and stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o022, "DIRECTORY_UNSAFE")
    try:
        require("system.posix_acl_default" not in os.listxattr(path), "DIRECTORY_DEFAULT_ACL_REQUIRES_REVIEW")
    except (OSError, AttributeError):
        raise Refusal("DIRECTORY_ACL_CHECK_UNAVAILABLE") from None


def read_env():
    require(ENV_FILE.resolve(strict=True) == ENV_FILE, "SHARED_ENV_PATH_CHANGED")
    root_directory(ENV_FILE.parent)
    fd = os.open(ENV_FILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "ENV_NOT_SINGLE_REGULAR_FILE")
        require(info.st_size <= 262144 and not info.st_mode & 0o007, "ENV_SIZE_OR_PERMISSIONS_UNSAFE")
        try:
            require(not os.listxattr(fd), "ENV_EXTENDED_ATTRIBUTES_REQUIRE_REVIEW")
        except (OSError, AttributeError):
            raise Refusal("ENV_ATTRIBUTE_CHECK_UNAVAILABLE") from None
        data = os.read(fd, 262145)
        require(len(data) == info.st_size, "ENV_CHANGED_WHILE_READING")
        return FileSnapshot(data, (info.st_dev, info.st_ino, info.st_mtime_ns),
                            info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
    finally:
        os.close(fd)


def key_span(data):
    lines = list(KEY_LINE.finditer(data))
    require(len(lines) == 1, "EXPECTED_ONE_STRIPE_SECRET_KEY_ASSIGNMENT")
    value = KEY_VALUE.fullmatch(lines[0].group(1))
    require(value is not None, "EXISTING_KEY_IS_NOT_PLAIN_TEST_SECRET")
    group = 2 if value.group(2) else 3
    start = lines[0].start(1) + value.start(group)
    end = lines[0].start(1) + value.end(group)
    return start, end, value.group(group).decode("ascii")


def replacement_bytes(data, new_key):
    require(re.fullmatch(r"sk_test_[A-Za-z0-9]{16,240}", new_key) is not None,
            "REPLACEMENT_MUST_BE_TEST_SECRET")
    start, end, old_key = key_span(data)
    require(new_key != old_key, "REPLACEMENT_EQUALS_EXPIRED_KEY")
    return data[:start] + new_key.encode("ascii") + data[end:]


def service_snapshot(file_snapshot):
    output = command(["systemctl", "show", SERVICE, "-p", "ActiveState", "-p", "MainPID",
                      "-p", "WorkingDirectory", "-p", "EnvironmentFiles", "-p", "Environment"])
    props = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    require(props.get("ActiveState") == "active", "BACKEND_NOT_ACTIVE")
    pid = int(props.get("MainPID", "0"))
    require(pid > 1 and props.get("WorkingDirectory") == str(CURRENT), "SERVICE_IDENTITY_CHANGED")
    require(CURRENT.is_symlink(), "CURRENT_RELEASE_NOT_SYMLINK")
    release = CURRENT.resolve(strict=True)
    require(release.is_relative_to(CURRENT.parent / "releases"), "RELEASE_OUTSIDE_EXPECTED_ROOT")
    require(Path(f"/proc/{pid}/cwd").resolve(strict=True) == release, "RUNNING_RELEASE_MISMATCH")
    require((release / ".env").is_symlink() and (release / ".env").resolve(strict=True) == ENV_FILE,
            "RELEASE_ENV_LINK_CHANGED")
    require(json.loads((release / "release.json").read_text())["git_sha"] == BACKEND_SHA,
            "BACKEND_REVISION_CHANGED")
    consumer = release / "apps/trips/consumers.py"
    require(hashlib.sha256(consumer.read_bytes()).hexdigest() == CONSUMER_SHA256,
            "BACKEND_APPLICATION_BYTES_CHANGED")
    require(not any(item.startswith("STRIPE_SECRET_KEY=")
                    for item in shlex.split(props.get("Environment", ""))),
            "EXPLICIT_SERVICE_KEY_OVERRIDE_REQUIRES_REVIEW")
    env_files = props.get("EnvironmentFiles", "")
    from_shared = re.fullmatch(re.escape(str(ENV_FILE)) + r"(?: \(ignore_errors=(?:yes|no)\))?", env_files)
    require(not env_files or from_shared, "OTHER_ENVIRONMENT_FILES_REQUIRE_REVIEW")
    initial_env = Path(f"/proc/{pid}/environ").read_bytes()
    inherited = [part.split(b"=", 1)[1] for part in initial_env.split(b"\0")
                 if part.startswith(b"STRIPE_SECRET_KEY=")]
    if from_shared:
        require(inherited == [key_span(file_snapshot.data)[2].encode("ascii")],
                "INHERITED_KEY_DOES_NOT_MATCH_SHARED_FILE")
    else:
        require(not inherited, "INHERITED_SERVICE_KEY_OVERRIDE_REQUIRES_REVIEW")
    return {"pid": pid, "release": str(release),
            "key_source": "systemd-shared-env" if from_shared else "django-shared-env"}


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(SOCKET)


def readiness():
    connection = UnixConnection("localhost", timeout=5)
    try:
        connection.request("GET", "/api/trips/list-trips/", headers={
            "Host": "airportandcitytransfer.com", "X-Forwarded-Proto": "https"})
        response = connection.getresponse()
        response.read(4096)
        require(response.status in (401, 403), "UNEXPECTED_BACKEND_READINESS")
        return response.status
    finally:
        connection.close()


def stripe_response(path, key):
    connection = http.client.HTTPSConnection("api.stripe.com", timeout=10,
                                           context=ssl.create_default_context())
    try:
        connection.request("GET", path, headers={"Authorization": "Bearer " + key,
                            "User-Agent": "ACT-test-key-recovery/20261117"})
        response = connection.getresponse()
        body = response.read(131073)
        require(len(body) <= 131072, "STRIPE_RESPONSE_TOO_LARGE")
        return response.status, json.loads(body)
    finally:
        connection.close()


def stripe_get(path, key):
    status_code, data = stripe_response(path, key)
    require(status_code == 200, "STRIPE_TEST_KEY_VALIDATION_FAILED")
    return data


def require_expired_current_key(snapshot):
    status_code, data = stripe_response("/v1/account", key_span(snapshot.data)[2])
    error = data.get("error", {})
    require(status_code == 401 and (error.get("code") == "api_key_expired" or
            str(error.get("message", "")).startswith("Expired API Key provided:")),
            "EXISTING_KEY_NOT_CONFIRMED_EXPIRED_NO_UPDATE")


def validate_key(key):
    require(re.fullmatch(r"sk_test_[A-Za-z0-9]{16,240}", key) is not None,
            "REPLACEMENT_MUST_BE_TEST_SECRET")
    require(stripe_get("/v1/account", key).get("id") == ACCOUNT, "STRIPE_ACCOUNT_MISMATCH")
    require(stripe_get("/v1/balance", key).get("livemode") is False, "STRIPE_TEST_MODE_NOT_CONFIRMED")


def hidden_key():
    require(sys.stdin.isatty() and sys.stderr.isatty(), "INTERACTIVE_TERMINAL_REQUIRED")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass("Paste ACT Stripe TEST secret (hidden): ", stream=sys.stderr)


def same_file(expected, current):
    return (expected.identity, expected.uid, expected.gid, expected.mode, expected.data) == (
        current.identity, current.uid, current.gid, current.mode, current.data)


def atomic_replace(snapshot, data):
    require(same_file(snapshot, read_env()), "ENV_CHANGED_NO_UPDATE")
    fd, temp_name = tempfile.mkstemp(prefix=".act-stripe-", dir=ENV_FILE.parent)
    try:
        os.fchown(fd, snapshot.uid, snapshot.gid)
        os.fchmod(fd, snapshot.mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        require(same_file(snapshot, read_env()), "ENV_CHANGED_NO_UPDATE")
        os.replace(temp_name, ENV_FILE)
        directory = os.open(ENV_FILE.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def backup(data):
    if not BACKUP_ROOT.exists():
        BACKUP_ROOT.mkdir(mode=0o700)
    root_directory(BACKUP_ROOT)
    directory = Path(tempfile.mkdtemp(prefix="stripe-test-key-", dir=BACKUP_ROOT))
    path = directory / "backend.env.before"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return str(path)


def apply(snapshot, before, status, new_key):
    global MUTATION_STAGE
    require_expired_current_key(snapshot)
    validate_key(new_key)
    updated = replacement_bytes(snapshot.data, new_key)
    require(service_snapshot(snapshot) == before, "SERVICE_CHANGED_NO_UPDATE")
    require(same_file(snapshot, read_env()), "ENV_CHANGED_NO_UPDATE")
    backup_path = backup(snapshot.data)
    print("PRIVATE_BACKUP=" + backup_path, flush=True)
    MUTATION_STAGE = "CONFIG_UPDATE_STARTED"
    try:
        atomic_replace(snapshot, updated)
    except Refusal:
        raise
    except OSError:
        raise Refusal("ENV_WRITE_RESULT_UNCONFIRMED_BACKUP_RETAINED") from None
    MUTATION_STAGE = "CONFIG_UPDATED"
    try:
        require(service_snapshot(snapshot) == before, "SERVICE_DRIFT")
        written = read_env()
        require(written.data == updated and (written.uid, written.gid, written.mode) ==
                (snapshot.uid, snapshot.gid, snapshot.mode), "ENV_DRIFT")
    except Exception:
        raise Refusal("KEY_UPDATED_SERVICE_OR_ENV_CHANGED_NOT_RESTARTED_BACKUP_RETAINED") from None
    print("TEST_SECRET_UPDATED; RESTARTING_ACT_BACKEND", flush=True)
    MUTATION_STAGE = "RESTART_REQUESTED"
    try:
        restarted = subprocess.run(["systemctl", "restart", SERVICE], capture_output=True, timeout=25)
    except (subprocess.TimeoutExpired, OSError):
        raise Refusal("KEY_UPDATED_RESTART_RESULT_UNKNOWN_BACKUP_RETAINED") from None
    if restarted.returncode != 0:
        raise Refusal("KEY_UPDATED_RESTART_FAILED_BACKUP_RETAINED")
    MUTATION_STAGE = "RESTART_RETURNED_SUCCESS"
    for attempt in range(3):
        try:
            after = read_env()
            require(after.data == updated, "POST_UPDATE_ENV_DRIFT")
            running = service_snapshot(after)
            require(running["pid"] != before["pid"] and running["release"] == before["release"]
                    and running["key_source"] == before["key_source"], "RESTART_IDENTITY_UNCONFIRMED")
            require(readiness() == status, "BACKEND_READINESS_CHANGED")
            print("APPLIED_RESTARTED_GUEST_CHECK_PENDING")
            return
        except (Refusal, OSError, http.client.HTTPException):
            if attempt < 2:
                time.sleep(1)
    raise Refusal("KEY_UPDATED_READINESS_UNCONFIRMED_BACKUP_RETAINED")


def main():
    parser = SafeArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Read-only configuration source check (default)")
    group.add_argument("--apply", action="store_true", help="Hidden key entry, approved test-secret update and one restart")
    args = parser.parse_args()
    require(os.geteuid() == 0, "ROOT_VPS_TERMINAL_REQUIRED")
    lock = None
    try:
        if args.apply:
            lock = os.open(LOCK_FILE, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            lock_info = os.fstat(lock)
            require(lock_info.st_uid == 0 and stat.S_ISREG(lock_info.st_mode)
                    and lock_info.st_nlink == 1 and not lock_info.st_mode & 0o022, "LOCK_FILE_UNSAFE")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refusal("EXISTING_BACKEND_DEPLOYMENT_LOCK_BUSY_NO_UPDATE") from None
        snapshot = read_env()
        key_span(snapshot.data)
        before = service_snapshot(snapshot)
        status = readiness()
        print(json.dumps({"status": "READY_FOR_TEST_SECRET_REPLACEMENT", "service": SERVICE,
                          "env_file": str(ENV_FILE), "key_source": before["key_source"],
                          "existing_key_mode": "test", "backend_sha": BACKEND_SHA,
                          "readiness_http": status}))
        if args.apply:
            apply(snapshot, before, status, hidden_key())
    finally:
        if lock is not None:
            os.close(lock)


if __name__ == "__main__":
    try:
        main()
    except Refusal as error:
        print("STOPPED: " + str(error) + "; STAGE=" + MUTATION_STAGE, file=sys.stderr)
        sys.exit(1)
    except (Exception, KeyboardInterrupt):
        # Never render provider response bodies, configuration, or exception values.
        print("STOPPED: CHECK_FAILED_OR_INTERRUPTED; STAGE=" + MUTATION_STAGE +
              "; NO_SECRET_DETAILS_PRINTED", file=sys.stderr)
        sys.exit(1)
