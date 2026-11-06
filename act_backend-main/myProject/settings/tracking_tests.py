"""Isolated settings for the focused real-model tracking access tests only."""

import os

if os.environ.get("ACT_TRACKING_ACCESS_TESTS") != "1":
    raise RuntimeError("Tracking test settings require ACT_TRACKING_ACCESS_TESTS=1")

from .base import *  # noqa: E402,F403

if DATABASES["default"]["HOST"] != "127.0.0.1" or DATABASES["default"]["NAME"] != "act_tracking_test":
    raise RuntimeError("Tracking tests require the isolated loopback act_tracking_test database")

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
ROOT_URLCONF = "apps.trips.tests.tracking_test_urls"
MIDDLEWARE = []
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_IGNORE_RESULT = True
CELERY_BEAT_SCHEDULE = {}
N8N_ENABLED = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
