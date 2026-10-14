"""Encryption helper for TfL operator records; never log or expose plaintext NI."""
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def encrypt_operator_ni(normalized_national_insurance):
    """Encrypt a validated NINO using a separately managed ACT-owned key."""
    key = getattr(settings, "ACT_NI_ENCRYPTION_KEY", "")
    if not isinstance(key, str) or not key:
        raise ImproperlyConfigured("ACT_NI_ENCRYPTION_KEY is required for approval")
    try:
        cipher = Fernet(key.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured("Invalid ACT NI encryption-key configuration") from exc
    return "fernet:v1:" + cipher.encrypt(normalized_national_insurance.encode("ascii")).decode("ascii")


def decrypt_operator_ni(ciphertext):
    """For future access-controlled operator compliance export only."""
    if not ciphertext.startswith("fernet:v1:"):
        raise ValueError("Unknown operator-record encryption format")
    key = getattr(settings, "ACT_NI_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured("ACT NI encryption key unavailable")
    return Fernet(key.encode("ascii")).decrypt(ciphertext[len("fernet:v1:"):].encode("ascii")).decode("ascii")
