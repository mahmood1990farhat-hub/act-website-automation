import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_event(event_name, payload):
    """
    Send a signed event to n8n.

    Safe-failure behavior:
    - Returns False on any failure
    - Never raises, so caller business logic is not interrupted
    """
    if not getattr(settings, "N8N_ENABLED", False):
        return False

    url = getattr(settings, "N8N_WEBHOOK_URL", None)
    secret_value = getattr(settings, "N8N_SECRET", None)
    if not url or not secret_value:
        logger.warning("n8n skipped: missing N8N_WEBHOOK_URL or N8N_SECRET")
        return False

    body = {"event": event_name, "data": payload}
    raw_body = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret_value.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
    }

    try:
        response = requests.post(url, data=raw_body, headers=headers, timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("n8n webhook failed for event=%s", event_name)
        return False
