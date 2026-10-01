"""Minimal Django smoke-test settings, NOT the ACT application settings."""
SECRET_KEY = 'synthetic-isolation-only-not-for-deployment'
DEBUG = False
INSTALLED_APPS = []
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'test@example.invalid'
USE_TZ = True
MIDDLEWARE = []
ALLOWED_HOSTS = []
