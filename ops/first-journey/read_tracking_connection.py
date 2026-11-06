#!/usr/bin/env python3
"""Read-only, bounded diagnosis of ACT's existing tracking connection.

Three tokenless requests use synthetic trip 0: public TLS, loopback TLS with
the same verified hostname, and the existing Unix socket. A pass requires the
WebSocket upgrade followed by auth_error and close 4403. No credentials, real
trip, GPS, application imports, settings changes, file writes or service control.
Only fixed result codes are printed; response headers/messages are never shown.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import base64
import hashlib
import json
import multiprocessing
import os
import re
import select
import socket
import ssl
import struct
import subprocess
import time

DOMAIN = "airportandcitytransfer.com"
WS_PATH = "/ws/trips/0/tracking/"
UNIX_SOCKET = "/run/act.sock"
PROBE_SECONDS = 8.0
TOTAL_SECONDS = 35.0
MAX_HEADERS = 8192
MAX_FRAME = 4096
MAX_JOURNAL_BYTES = 262144


class RefusalCheckFailed(Exception):
    """Contains a fixed, safe-to-print diagnostic code, never peer text."""


def require(condition, code):
    if not condition:
        raise RefusalCheckFailed(code)


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError
    return value


def recv_exact(connection, count, deadline):
    body = bytearray()
    while len(body) < count:
        connection.settimeout(remaining(deadline))
        part = connection.recv(count - len(body))
        require(bool(part), "PEER_CLOSED_EARLY")
        body.extend(part)
    return bytes(body)


def send(connection, body, deadline):
    connection.settimeout(remaining(deadline))
    connection.sendall(body)


def frame(connection, deadline):
    first, second = recv_exact(connection, 2, deadline)
    require(first & 0x80 and not first & 0x70 and not second & 0x80,
            "INVALID_FRAME_FLAGS")
    size = second & 0x7f
    if size == 126:
        size = struct.unpack("!H", recv_exact(connection, 2, deadline))[0]
    elif size == 127:
        size = struct.unpack("!Q", recv_exact(connection, 8, deadline))[0]
    require(size <= MAX_FRAME, "FRAME_TOO_LARGE")
    return first & 0x0f, recv_exact(connection, size, deadline)


def masked_frame(opcode, body):
    require(len(body) < 126, "CLIENT_FRAME_TOO_LARGE")
    mask = os.urandom(4)
    return bytes([0x80 | opcode, 0x80 | len(body)]) + mask + bytes(
        value ^ mask[index % 4] for index, value in enumerate(body)
    )


def next_frame(connection, deadline):
    # A bounded number of ordinary server keepalive pings may precede a reply.
    for _ in range(5):
        opcode, body = frame(connection, deadline)
        if opcode != 9:
            return opcode, body
        require(len(body) <= 125, "INVALID_PING")
        send(connection, masked_frame(10, body), deadline)
    raise RefusalCheckFailed("TOO_MANY_CONTROL_FRAMES")


def check_refusal(connection, deadline, phase, *, unix=False):
    phase("HTTP_UPGRADE")
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    forwarded = "X-Forwarded-Proto: https\r\n" if unix else ""
    request = (
        f"GET {WS_PATH} HTTP/1.1\r\nHost: {DOMAIN}\r\n"
        f"Origin: https://{DOMAIN}\r\nUpgrade: websocket\r\n"
        "Connection: Upgrade\r\nSec-WebSocket-Version: 13\r\n"
        f"Sec-WebSocket-Key: {key}\r\n{forwarded}\r\n"
    ).encode("ascii")
    send(connection, request, deadline)
    header = bytearray()
    while not header.endswith(b"\r\n\r\n"):
        require(len(header) < MAX_HEADERS, "HEADERS_TOO_LARGE")
        header.extend(recv_exact(connection, 1, deadline))
    lines = bytes(header).decode("iso-8859-1").split("\r\n")
    match = re.fullmatch(r"HTTP/1\.[01] ([0-9]{3})(?: .*|)", lines[0])
    require(match is not None, "INVALID_HTTP_STATUS")
    status = match.group(1)
    require(status == "101", "HTTP_" + status)
    fields = {}
    for line in lines[1:]:
        if not line:
            continue
        require(":" in line, "INVALID_UPGRADE_HEADER")
        name, value = line.split(":", 1)
        name = name.lower().strip()
        if name in ("sec-websocket-accept", "upgrade", "connection"):
            require(name not in fields, "DUPLICATE_UPGRADE_HEADER")
            fields[name] = value.strip()
    expected = base64.b64encode(hashlib.sha1(
        (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
    ).digest()).decode("ascii")
    require(fields.get("sec-websocket-accept") == expected, "INVALID_UPGRADE_ACCEPT")
    require(fields.get("upgrade", "").lower() == "websocket", "MISSING_UPGRADE_HEADER")
    require("upgrade" in [part.strip().lower() for part in fields.get("connection", "").split(",")],
            "MISSING_CONNECTION_UPGRADE")
    phase("ANONYMOUS_AUTH_REFUSAL")
    send(connection, masked_frame(1, b'{"type":"viewer_auth"}'), deadline)
    opcode, body = next_frame(connection, deadline)
    require(opcode == 1, "EXPECTED_AUTH_ERROR_MESSAGE")
    try:
        reply = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise RefusalCheckFailed("INVALID_AUTH_REPLY") from None
    require(reply == {"type": "auth_error"}, "EXPECTED_AUTH_ERROR_MESSAGE")
    phase("AUTH_REFUSAL_CLOSE")
    opcode, body = next_frame(connection, deadline)
    require(opcode == 8 and 2 <= len(body) <= 125, "EXPECTED_AUTH_ERROR_CLOSE")
    close_code = struct.unpack("!H", body[:2])[0]
    require(close_code == 4403, "CLOSE_" + str(close_code))


def probe_worker(kind, output, seconds):
    """The parent hard-stops this child even if DNS ignores socket timeouts."""
    phase = "START"

    def mark(value):
        nonlocal phase
        phase = value
        try:
            output.send(("phase", value))
        except (BrokenPipeError, EOFError, OSError):
            pass

    deadline = time.monotonic() + seconds
    try:
        if kind == "UNIX_BACKEND":
            mark("UNIX_CONNECT")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(remaining(deadline))
                connection.connect(UNIX_SOCKET)
                check_refusal(connection, deadline, mark, unix=True)
        else:
            mark("PUBLIC_DNS_AND_TCP" if kind == "PUBLIC_WSS" else "LOOPBACK_TCP")
            address = DOMAIN if kind == "PUBLIC_WSS" else "127.0.0.1"
            with socket.create_connection((address, 443), timeout=remaining(deadline)) as raw:
                mark("VERIFIED_TLS")
                # Avoid create_default_context's SSLKEYLOGFILE handling: no key log writes.
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_default_certs()
                raw.settimeout(remaining(deadline))
                with context.wrap_socket(raw, server_hostname=DOMAIN) as connection:
                    check_refusal(connection, deadline, mark)
        result = {"status": "PASS", "phase": "COMPLETE", "code": "ANONYMOUS_REFUSED_4403"}
    except RefusalCheckFailed as error:
        result = {"status": "FAIL", "phase": phase, "code": str(error)}
    except ssl.SSLCertVerificationError:
        result = {"status": "FAIL", "phase": phase, "code": "TLS_CERTIFICATE_VERIFICATION"}
    except ssl.SSLError:
        result = {"status": "FAIL", "phase": phase, "code": "TLS_HANDSHAKE"}
    except (TimeoutError, socket.timeout):
        result = {"status": "FAIL", "phase": phase, "code": "TIMEOUT"}
    except socket.gaierror:
        result = {"status": "FAIL", "phase": phase, "code": "DNS_RESOLUTION"}
    except (ConnectionError, FileNotFoundError, PermissionError):
        result = {"status": "FAIL", "phase": phase, "code": "ENDPOINT_UNREACHABLE"}
    except Exception:
        result = {"status": "FAIL", "phase": phase, "code": "LOCAL_OR_PROTOCOL_ERROR"}
    try:
        output.send(("result", result))
    except (BrokenPipeError, EOFError, OSError):
        pass
    finally:
        output.close()


def isolated_probe(kind, overall_deadline):
    seconds = min(PROBE_SECONDS, max(0.0, overall_deadline - time.monotonic() - 1.0))
    if seconds <= 0:
        return {"status": "SKIPPED", "phase": "START", "code": "OVERALL_DEADLINE"}
    context = multiprocessing.get_context("fork")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=probe_worker, args=(kind, writer, seconds), daemon=True)
    process.start()
    writer.close()
    deadline = time.monotonic() + seconds
    phase, result = "START", None
    try:
        while time.monotonic() < deadline:
            if not reader.poll(max(0.0, deadline - time.monotonic())):
                break
            try:
                label, value = reader.recv()
            except EOFError:
                break
            if label == "phase":
                phase = value
            elif label == "result":
                result = value
                break
    finally:
        reader.close()
        process.join(timeout=0.1)
        if process.is_alive():
            process.terminate()
            process.join(timeout=0.3)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.3)
        process.close()
    return result or {"status": "FAIL", "phase": phase, "code": "DEADLINE_OR_WORKER_EXIT"}


def recent_exception_counts(overall_deadline):
    """Bounded act.service category counts only; never print journal messages."""
    patterns = {
        "redis_exception": r"redis\.exceptions\.(?:ConnectionError|TimeoutError|AuthenticationError|ResponseError)",
        "channel_layer_exception": r"(?:InvalidChannelLayerError|ChannelFull|MessageTooLarge)",
        "database_exception": r"(?:django\.db\.utils|psycopg2?(?:\.errors)?)\.(?:OperationalError|InterfaceError|DatabaseError|IntegrityError|InternalError|ProgrammingError|DataError|UniqueViolation)",
        "auth_exception": r"(?:InvalidToken|TokenError|AuthenticationFailed|PermissionDenied)",
        "application_exception": r"Exception inside application|Traceback \(most recent call last\)",
    }
    counts = {name: 0 for name in patterns}
    deadline = min(overall_deadline - 0.5, time.monotonic() + 2.5)
    if deadline <= time.monotonic():
        return {"status": "SKIPPED", "code": "OVERALL_DEADLINE"}
    process = None
    raw = bytearray()
    try:
        process = subprocess.Popen(
            ["/usr/bin/journalctl", "--unit=act.service", "--since=-20min", "--lines=200",
             "--output=json", "--no-pager", "--quiet"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        while len(raw) < MAX_JOURNAL_BYTES and time.monotonic() < deadline:
            ready, _, _ = select.select([process.stdout], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                break
            part = os.read(process.stdout.fileno(), min(8192, MAX_JOURNAL_BYTES - len(raw)))
            if not part:
                break
            raw.extend(part)
        complete = process.poll() == 0 and len(raw) < MAX_JOURNAL_BYTES
        entries = 0
        for line in raw.splitlines():
            try:
                entry = json.loads(line)
                message = entry.get("MESSAGE", "")
            except (ValueError, AttributeError, UnicodeError):
                continue
            if not isinstance(message, str):
                continue
            entries += 1
            for category, pattern in patterns.items():
                counts[category] += bool(re.search(pattern, message))
        return {"status": "COMPLETE" if complete else "PARTIAL", "scope": "ACT_SERVICE_LAST_20_MIN_MAX_200_ENTRIES",
                "entries_examined": entries, "matching_entries": counts}
    except Exception:
        return {"status": "UNAVAILABLE", "code": "JOURNAL_SUMMARY_UNAVAILABLE"}
    finally:
        raw.clear()
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
            if process.stdout:
                process.stdout.close()


def main():
    if len(sys.argv) != 1:
        print("READ_ONLY_NOT_RUN: this fixed diagnostic accepts no arguments.")
        return 2
    deadline = time.monotonic() + TOTAL_SECONDS
    print("READ_ONLY_TRACKING_DIAGNOSTIC: synthetic trip 0; no credentials or location sent.", flush=True)
    results = {}
    for kind in ("PUBLIC_WSS", "ORIGIN_TLS", "UNIX_BACKEND"):
        results[kind] = isolated_probe(kind, deadline)
        print(kind + "=" + json.dumps(results[kind], sort_keys=True), flush=True)
    print("RECENT_EXCEPTION_CATEGORIES=" + json.dumps(recent_exception_counts(deadline), sort_keys=True), flush=True)
    print("READ_ONLY_COMPLETE: no settings, services, bookings or files changed.", flush=True)
    print("A pass proves anonymous refusal on that path; it does not prove authenticated GPS delivery.", flush=True)
    return 0 if all(item["status"] == "PASS" for item in results.values()) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("READ_ONLY_INTERRUPTED: no settings, services, bookings or files changed.")
        raise SystemExit(130) from None
    except Exception:
        print("READ_ONLY_INCOMPLETE: local diagnostic error; no raw exception output.")
        raise SystemExit(1) from None
