"""Booking-owned language; never infer it from a later staff/webhook request."""
from functools import wraps
from django.utils.translation import override

SUPPORTED_LANGUAGES = ("en", "ar", "fr", "de", "es", "tr", "zh-CN")


def normalize_language(value):
    value = str(value or "").strip().lower().replace("_", "-")
    # Keep the published Simplified Chinese identifier. Do not silently treat
    # Traditional Chinese (zh-TW/zh-Hant) as a translation we do not provide.
    if value in ("zh", "zh-cn", "zh-hans", "zh-hans-cn", "zh-sg"):
        return "zh-CN"
    base = value.split("-")[0]
    return base if base in SUPPORTED_LANGUAGES else "en"


def details_with_language(details, locale):
    result = dict(details) if isinstance(details, dict) else {}
    result["customer_language"] = normalize_language(locale)
    return result


def booking_language(trip):
    details = getattr(trip, "booking_details", None)
    return normalize_language(details.get("customer_language")) if isinstance(details, dict) else "en"


def use_booking_language(function):
    @wraps(function)
    def wrapped(user, trip, *args, **kwargs):
        with override(booking_language(trip)):
            return function(user, trip, *args, **kwargs)
    return wrapped
