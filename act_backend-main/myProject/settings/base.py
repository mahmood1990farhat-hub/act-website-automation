import environ
from pathlib import Path
import os 
import sys
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --- From .env: security & hosts ---
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'channels',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'silk',
    'drf_yasg',
    'adminsortable2',
    'django.contrib.gis',


    # Local apps
    'apps.accounts',
    'apps.drivers',
    'apps.passengers',
    'apps.trips',
    'apps.payments',
    'apps.office',
    'apps.vehicle',
    'apps.complaints',
    'apps.pricing',
    'apps.earnings',
    'apps.admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "silk.middleware.SilkyMiddleware",
]

ROOT_URLCONF = 'myProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'myProject.wsgi.application'
ASGI_APPLICATION = 'myProject.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# --- From .env: database ---
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
LANGUAGES = [('en', 'English'), ('ar', 'Arabic')]
LOCALE_PATHS = [BASE_DIR / 'locale']




APP_BASE_URL = env("APP_BASE_URL", default="http://127.0.0.1:8000").rstrip("/")
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Public base URL for email image assets.
# You can override this in .env (recommended in production/CDN).
ACT_EMAIL_ASSETS_BASE_URL = env(
    "ACT_EMAIL_ASSETS_BASE_URL",
    default=f"{APP_BASE_URL}{STATIC_URL}email-assets",
)

 





DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "utils.common.exception_handler.custom_exception_handler",
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    'BLACKLIST_AFTER_ROTATION': True,
    'ROTATE_REFRESH_TOKENS': True,
    "USER_AUTHENTICATION_RULE": "accounts.authentication.allow_inactive_user",
}


AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = [
    'accounts.authentication.EmailOrPhoneAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]



TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_VERIFY_SERVICE_SID = env('TWILIO_VERIFY_SERVICE_SID')



GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY')


STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET')



import firebase_admin
from firebase_admin import credentials

FIREBASE_CREDENTIALS_PATH = BASE_DIR / env('FIREBASE_CREDENTIALS_PATH', default='airport-city-transfer-33ac7-firebase-adminsdk-fbsvc-aba3144ea6.json')

if FIREBASE_CREDENTIALS_PATH and FIREBASE_CREDENTIALS_PATH.exists():
    try:
        if not firebase_admin._apps:
            default_cred = credentials.Certificate(str(FIREBASE_CREDENTIALS_PATH))
            firebase_admin.initialize_app(default_cred)
            print(f"✅ Firebase initialized successfully with credentials: {FIREBASE_CREDENTIALS_PATH}")
        else:
            print(f"ℹ️  Firebase app already initialized")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize Firebase app: {e}")
else:
    print(f"⚠️  Warning: Firebase credentials file not found at {FIREBASE_CREDENTIALS_PATH}")




CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_BEAT_SCHEDULE = {
    "expire-old-trips-every-minute": {
        "task": "trips.tasks.expire_old_trips",
        "schedule": 60.0,
    },
}
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

NOTIFICATION_FORCE_SYNC = env.bool("NOTIFICATION_FORCE_SYNC", default=False)


EMAIL_BACKEND = "utils.common.email_backend.CustomSMTPEmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
ADMIN_EMAIL = env("ADMIN_EMAIL")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

EMAIL_SSL_VERIFY = env.bool("EMAIL_SSL_VERIFY", default=True)

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB in bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB in bytes
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

TRIP_BUFFER_MINUTES = env.int('TRIP_BUFFER_MINUTES', default=60)

# n8n outbound webhook integration
N8N_ENABLED = env.bool("N8N_ENABLED", default=True)
N8N_WEBHOOK_URL = env("N8N_WEBHOOK_URL", default="https://airportandcitytransfer.app.n8n.cloud/webhook-test/driver-onboarding")
N8N_SECRET = env("N8N_SECRET", default="act-n8n-secret-dev")
