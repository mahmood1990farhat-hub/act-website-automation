#!/usr/bin/env python3
"""Read-only ACT Stripe test PaymentIntent/public-key compatibility check.

No card data, new PaymentIntents, configuration changes, service actions or
credential values are accepted on the command line or printed. Requires the
private, previously captured frontend build-time public configuration and the
existing backend recovery helper. This checks the captured frontend key, NOT
independently the JavaScript currently served to browsers.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import quote

import replace_expired_test_key as recovery

FRONTEND_PUBLIC_ENV = Path(
    "/root/act-release-backup/tracking-stage-oe9oh1vi/frontend-public-environment.json"
)
INTENT_ID = re.compile(r"pi_[A-Za-z0-9]{12,48}\Z")
PUBLIC_TEST_KEY = re.compile(r"pk_test_[A-Za-z0-9]{16,240}\Z")


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise recovery.Refusal("EXPECTED_ONLY_PAYMENT_INTENT_ID_NO_KEYS")


def captured_public_key():
    """Read an existing root-private configuration receipt, without echoing it."""
    fd = os.open(FRONTEND_PUBLIC_ENV, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        recovery.require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and before.st_uid == 0 and not (stat.S_IMODE(before.st_mode) & 0o077)
            and before.st_size <= 65536,
            "FRONTEND_RECEIPT_NOT_ROOT_PRIVATE",
        )
        raw = os.read(fd, 65537)
        after = os.fstat(fd)
        recovery.require(
            len(raw) == before.st_size and
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "FRONTEND_RECEIPT_CHANGED",
        )
        settings = json.loads(raw)
    finally:
        os.close(fd)
    recovery.require(isinstance(settings, dict), "FRONTEND_RECEIPT_INVALID")
    public_key = settings.get("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", "")
    recovery.require(isinstance(public_key, str) and
                     PUBLIC_TEST_KEY.fullmatch(public_key) is not None,
                     "CAPTURED_PUBLIC_KEY_NOT_TEST_MODE")
    return public_key


def check(payment_intent_id):
    recovery.require(os.geteuid() == 0, "ROOT_READ_ONLY_TERMINAL_REQUIRED")
    recovery.require(isinstance(payment_intent_id, str) and
                     INTENT_ID.fullmatch(payment_intent_id) is not None,
                     "INVALID_PAYMENT_INTENT_ID")

    # Reuse existing guarded live-service and shared-env checks. No modifications.
    snapshot = recovery.read_env()
    recovery.service_snapshot(snapshot)
    secret = recovery.key_span(snapshot.data)[2]
    public = captured_public_key()

    account_status, account = recovery.stripe_response("/v1/account", secret)
    recovery.require(account_status == 200 and isinstance(account, dict) and
                     account.get("id") == recovery.ACCOUNT,
                     "BACKEND_TEST_ACCOUNT_NOT_VERIFIED")
    status, intent = recovery.stripe_response(
        "/v1/payment_intents/" + payment_intent_id, secret
    )
    recovery.require(status == 200 and isinstance(intent, dict) and
                     intent.get("id") == payment_intent_id and
                     intent.get("livemode") is False,
                     "EXISTING_TEST_INTENT_NOT_VERIFIED")
    recovery.require(intent.get("status") == "requires_payment_method" and
                     intent.get("payment_method") is None and
                     intent.get("amount_received") == 0,
                     "INTENT_STATE_CHANGED_STOP_BEFORE_DIAGNOSIS")
    client_secret = intent.get("client_secret")
    recovery.require(isinstance(client_secret, str) and
                     re.fullmatch(re.escape(payment_intent_id) +
                                  r"_secret_[A-Za-z0-9]{8,240}", client_secret) is not None,
                     "CLIENT_SECRET_NOT_VALID_FOR_INTENT")

    # Documented Stripe GET operation; no confirmation/POST and no card data.
    # Never expose/log the query, which contains the client's capability token.
    public_status, observed = recovery.stripe_response(
        "/v1/payment_intents/" + payment_intent_id +
        "?client_secret=" + quote(client_secret, safe=""), public
    )
    recovery.require(isinstance(observed, dict), "PUBLIC_READ_RESPONSE_INVALID")
    if public_status == 200 and observed.get("id") == payment_intent_id and observed.get("livemode") is False:
        return "CAPTURED_PUBLIC_KEY_CAN_READ_EXISTING_TEST_INTENT"
    safe_error = observed.get("error") if isinstance(observed.get("error"), dict) else {}
    if public_status == 404 and safe_error.get("code") == "resource_missing":
        return "CAPTURED_PUBLIC_KEY_CANNOT_FIND_EXISTING_TEST_INTENT"
    if public_status in (401, 403):
        return "CAPTURED_PUBLIC_KEY_REJECTED"
    return "PUBLIC_READ_NOT_VERIFIED"


def main(argv=None):
    try:
        parser = SafeParser(description="Read-only existing ACT test PaymentIntent check")
        parser.add_argument("--payment-intent-id", required=True)
        args = parser.parse_args(argv)
        result = check(args.payment_intent_id)
        print("READ_ONLY_STRIPE_CHECK: " + result + "; NO_CHANGES")
        return 0 if result == "CAPTURED_PUBLIC_KEY_CAN_READ_EXISTING_TEST_INTENT" else 2
    except recovery.Refusal as exc:
        print("STOPPED: " + str(exc) + "; NO_CHANGES", file=sys.stderr)
        return 1
    except Exception:
        print("STOPPED: READ_ONLY_DIAGNOSTIC_UNAVAILABLE; NO_CHANGES", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
