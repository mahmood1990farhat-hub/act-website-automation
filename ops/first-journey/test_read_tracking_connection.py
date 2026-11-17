"""Offline checks for the fixed, anonymous connection diagnostic; no host calls."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import struct
import time
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "read_tracking_connection", Path(__file__).with_name("read_tracking_connection.py")
)
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


def server_frame(opcode, body):
    return bytes([0x80 | opcode, len(body)]) + body


class FakeConnection:
    def __init__(self, reply=None, close_code=4403, http_status=101):
        self.reply = {"type": "auth_error"} if reply is None else reply
        self.close_code = close_code
        self.http_status = http_status
        self.sent = []
        self.pending = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def settimeout(self, *_):
        pass

    def connect(self, address):
        self.address = address

    def recv(self, count):
        part = bytes(self.pending[:count])
        del self.pending[:count]
        return part

    def sendall(self, data):
        self.sent.append(data)
        if data.startswith(b"GET "):
            key = next(line.split(b": ", 1)[1] for line in data.split(b"\r\n")
                       if line.startswith(b"Sec-WebSocket-Key: "))
            accept = base64.b64encode(hashlib.sha1(
                key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            ).digest())
            self.pending.extend(
                f"HTTP/1.1 {self.http_status} Response\r\n".encode()
                + b"Upgrade: websocket\r\nConnection: keep-alive,Upgrade\r\n"
                + b"Sec-WebSocket-Accept: " + accept + b"\r\n"
                + b"Set-Cookie: first=not-printed\r\nSet-Cookie: second=not-printed\r\n\r\n"
            )
        elif data[0] == 0x81:
            self.pending.extend(server_frame(1, json.dumps(self.reply).encode()))
            self.pending.extend(server_frame(8, struct.pack("!H", self.close_code)))


class Collector:
    def __init__(self):
        self.items = []

    def send(self, value):
        self.items.append(value)

    def close(self):
        pass


def blocked_worker(kind, output, seconds):
    output.send(("phase", "PUBLIC_DNS_AND_TCP"))
    time.sleep(10)


class DiagnosticProtocolTests(unittest.TestCase):
    def test_valid_refusal_uses_only_fixed_synthetic_path_and_tokenless_frame(self):
        connection = FakeConnection()
        phases = []
        diagnostic.check_refusal(connection, time.monotonic() + 1, phases.append)
        request, auth = connection.sent
        self.assertTrue(request.startswith(b"GET /ws/trips/0/tracking/ HTTP/1.1\r\n"))
        self.assertIn(b"Host: airportandcitytransfer.com\r\n", request)
        self.assertIn(b"Origin: https://airportandcitytransfer.com\r\n", request)
        self.assertNotIn(b"Authorization:", request)
        self.assertNotIn(b"Cookie:", request)
        self.assertEqual(auth[0], 0x81)
        self.assertTrue(auth[1] & 0x80)
        mask = auth[2:6]
        body = bytes(value ^ mask[index % 4] for index, value in enumerate(auth[6:]))
        self.assertEqual(body, b'{"type":"viewer_auth"}')
        self.assertEqual(phases[-1], "AUTH_REFUSAL_CLOSE")

    def test_unexpected_auth_payload_never_appears_in_result_or_output(self):
        secret = "PRIVATE_PAYLOAD_MUST_NOT_PRINT"
        connection = FakeConnection(reply={"type": "auth_ok", "detail": secret})
        collector, stdout, stderr = Collector(), io.StringIO(), io.StringIO()
        with mock.patch.object(diagnostic.socket, "socket", return_value=connection):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                diagnostic.probe_worker("UNIX_BACKEND", collector, 1)
        result = collector.items[-1][1]
        self.assertEqual(result["code"], "EXPECTED_AUTH_ERROR_MESSAGE")
        self.assertEqual(result["phase"], "ANONYMOUS_AUTH_REFUSAL")
        self.assertNotIn(secret, json.dumps(collector.items) + stdout.getvalue() + stderr.getvalue())
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")

    def test_incorrect_close_cannot_count_as_pass(self):
        with self.assertRaisesRegex(diagnostic.RefusalCheckFailed, "^CLOSE_1000$"):
            diagnostic.check_refusal(FakeConnection(close_code=1000), time.monotonic() + 1, lambda _: None)

    def test_http_failure_reports_only_status_number(self):
        with self.assertRaisesRegex(diagnostic.RefusalCheckFailed, "^HTTP_403$"):
            diagnostic.check_refusal(FakeConnection(http_status=403), time.monotonic() + 1, lambda _: None)

    def test_connection_errors_are_classified_without_exception_text(self):
        for error, expected in ((socket.gaierror("PRIVATE_DNS_DETAILS"), "DNS_RESOLUTION"),
                                (ConnectionRefusedError("PRIVATE_SOCKET_DETAILS"), "ENDPOINT_UNREACHABLE")):
            with self.subTest(expected=expected):
                collector = Collector()
                with mock.patch.object(diagnostic.socket, "create_connection", side_effect=error):
                    diagnostic.probe_worker("PUBLIC_WSS", collector, 1)
                self.assertEqual(collector.items[-1][1]["code"], expected)
                self.assertNotIn("PRIVATE_", json.dumps(collector.items))

    def test_parent_stops_a_worker_that_ignores_socket_timeouts(self):
        started = time.monotonic()
        with mock.patch.object(diagnostic, "probe_worker", blocked_worker):
            with mock.patch.object(diagnostic, "PROBE_SECONDS", 0.05):
                result = diagnostic.isolated_probe("PUBLIC_WSS", time.monotonic() + 2)
        self.assertEqual(result["phase"], "PUBLIC_DNS_AND_TCP")
        self.assertEqual(result["code"], "DEADLINE_OR_WORKER_EXIT")
        self.assertLess(time.monotonic() - started, 1.5)


if __name__ == "__main__":
    unittest.main()
