"""
Django settings for the Tamer Hosny catalog backend.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = BASE_DIR / 'credentials' / '.env'
if not ENV_PATH.exists():
    raise FileNotFoundError(
        f'Missing {ENV_PATH}. Copy credentials/.env.example to credentials/.env and fill in the secrets.'
    )
# override=True: runserver's autoreloader restarts the worker via
# os.execv, which *inherits* the current process environment rather
# than starting fresh - so without this, whatever credentials/.env
# contained the very first time this process chain started stays stuck
# in os.environ forever (load_dotenv's default is to never overwrite an
# already-set variable), and edits to the file silently never take
# effect until the whole dev server is killed and restarted from
# scratch.
load_dotenv(ENV_PATH, override=True)


def env(key, default=None, required=False):
    value = os.environ.get(key, default)
    if required and not value:
        raise RuntimeError(f'Missing required environment variable: {key}')
    return value


def env_bool(key, default=False):
    return str(os.environ.get(key, default)).lower() in ('1', 'true', 'yes', 'on')


def env_list(key, default=''):
    return [item.strip() for item in os.environ.get(key, default).split(',') if item.strip()]


SECRET_KEY = env('DJANGO_SECRET_KEY', required=True)
DEBUG = env_bool('DJANGO_DEBUG', False)

# Behind nginx terminating TLS and proxying over plain HTTP - without
# this, request.is_secure() (and anything built on it: sitemap/robots
# URLs, secure-cookie logic, redirect schemes) reads every request as
# HTTP, since Django only sees the proxy's own local connection.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

# Obfuscated, non-guessable admin/dashboard paths (never the defaults).
ADMIN_URL_PATH = env('DJANGO_ADMIN_URL_PATH', required=True)
DASHBOARD_URL_PATH = env('DASHBOARD_URL_PATH', required=True)

# Symmetric key used to encrypt/decrypt the auth cookies (must be exactly 32 bytes).
COOKIE_ENCRYPTION_KEY = env('COOKIE_ENCRYPTION_KEY', required=True)

DYNAMIC_CSRF_TRUSTED_ORIGIN_REGEXES = env_list(
    'DYNAMIC_CSRF_TRUSTED_ORIGIN_REGEXES',
    r'^https://([a-zA-Z0-9-]+\.)?tamerhosny\.com$',
)


# Application definition

INSTALLED_APPS = [
    'daphne',  # must precede staticfiles so it takes over `runserver`
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.forms',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'backend.main_app',
    'backend.people_app',
    'backend.studios_app',
    'backend.links_app',
    'backend.music_app',
    'backend.media_app',
    'backend.concerts_app',
    'backend.ads_app',
    'backend.dashboard_app',
    'backend.analytics_app',
    'backend.website_app',
    'backend.ai_remix_app',
]

LOGIN_URL = 'dashboard_app:login'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Compresses every response (HTML/CSS/JS/JSON) - base.html alone is
    # ~2000 lines before a single page's own content, so this is a large,
    # free win on every request. Must sit this early (right after
    # security) per Django's docs, before anything that varies the
    # response by Accept-Encoding.
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'config.custom_packages.cookies.DynamicCSRFMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'config.custom_packages.cookies.CustomMiddleware',
    'config.custom_packages.cookies.DisableCSRFMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Widget templates (e.g. the custom circular avatar upload widget) live
# under frontend/, same as every other dashboard template — route form
# rendering through the project's own TEMPLATES config instead of the
# forms renderer's isolated default engine so that DIRS applies.
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Real-time features (e.g. "listening now" presence) go over this. Same
# Redis instance the app already has available; a separate REDIS_URL
# lets it point elsewhere in production without touching CACHES.
#
# Explicit socket_timeout (well above the 5s BZPOPMIN poll channels_redis
# blocks on internally) plus retry_on_timeout: without these the async
# redis client's own read timeout could race that poll and surface as a
# spurious `TimeoutError`, which channels treats as a hard failure and
# drops the socket - the client then reconnects a couple seconds later,
# repeating open/close on every hiccup instead of just retrying quietly.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [{

                'address': env('REDIS_URL', 'redis://127.0.0.1:6379/0'),
                'socket_timeout': 30,
                'socket_connect_timeout': 10,
                'retry_on_timeout': True,
            }],
        },
    },
}

# Background jobs (e.g. the "Sing With Tamer" duet mix - AI vocal
# removal + audio mixing takes far too long to run in the request/
# response cycle without blocking every other visitor behind it on this
# single-process ASGI server). Same Redis instance as CHANNEL_LAYERS,
# just a different logical DB index so the two don't share a keyspace.
CELERY_BROKER_URL = env('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_TRACK_STARTED = True
# The duet mix is one long CPU-bound job per worker process at a time
# anyway (Spleeter/ffmpeg) - one prefetched task per worker keeps a
# slow job from starving others queued behind it.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

AUTH_USER_MODEL = 'main_app.UserAccount'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', required=True),
        'USER': env('DB_USER', required=True),
        'PASSWORD': env('DB_PASSWORD', required=True),
        'HOST': env('DB_HOST', 'localhost'),
        'PORT': env('DB_PORT', '5432'),
        # Reuse the TCP connection (and Postgres auth handshake) across
        # requests within a worker instead of opening a fresh one every
        # single time (Django's default, CONN_MAX_AGE=0) - a real
        # per-request cost even with Postgres on the same host.
        'CONN_MAX_AGE': int(env('DB_CONN_MAX_AGE', '60')),
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'ar'
LANGUAGES = [
    ('ar', 'العربية'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_TZ = True


# Static / media files

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Not '/media/' - that collides with the app's own '/media/<slug>/'
# route (movie/series/commercial detail pages). Locally that's masked
# because Django's own URL resolver always tries the app's routes
# first; in production nginx serves MEDIA_URL directly (by design, for
# performance) and intercepts the request before Django ever sees it,
# so '/media/<slug>/' 404s from nginx itself. MEDIA_ROOT (the actual
# disk path) is unaffected - only the URL prefix changes, so existing
# stored file paths keep working unchanged.
MEDIA_URL = 'uploads/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Email
#
# Prints to the console until EMAIL_HOST is filled in (dev-friendly: no
# real inbox needed to see the forgot-password code). Set EMAIL_HOST in
# credentials/.env to switch to real SMTP.
EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend'
    if env('EMAIL_HOST')
    else 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = env('EMAIL_HOST', '')
EMAIL_PORT = int(env('EMAIL_PORT', '587'))
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'no-reply@tamerhosny.local')


# Public website auth (separate from the internal dashboard login) -
# email/password signup plus "Sign in with Google". Client
# ID/secret are placeholders until the real Google Cloud OAuth
# credentials are dropped into credentials/.env; the button stays
# visible either way but errors clearly if clicked before that.
GOOGLE_OAUTH_CLIENT_ID = env('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = env('GOOGLE_OAUTH_CLIENT_SECRET', '')
GOOGLE_OAUTH_REDIRECT_URI = env(
    'GOOGLE_OAUTH_REDIRECT_URI', 'http://127.0.0.1:8600/auth/google/callback/',
)


# CORS

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOWED_ORIGIN_REGEXES = DYNAMIC_CSRF_TRUSTED_ORIGIN_REGEXES
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt',
    'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'ver', 'plat', 'sessiontoken', 'tk', 'ln',
]


# REST framework / JWT

REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_VERSION': 'v1',
    'VERSION_PARAM': 'version',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 35,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}


# Cache

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

