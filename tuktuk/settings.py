
import logging
import os
from datetime import timedelta
from pathlib import Path
import traceback

import requests
from dotenv import load_dotenv
from firebase_admin import initialize_app


load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = ["*"]
# CSRF_TRUSTED_ORIGINS = ['http://192.168.1.101']
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = True

SECRET_KEY = "fasdfadasd-+&0@5nf=k%zoyv5%u&f-$00@if(pvv9#2#15hw%tjb83pmdfdfa2y*"

DEBUG = bool(int(os.getenv("DEBUG")))
# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # Библиотеки
    "rest_framework",
    "rest_framework_gis",
    "drf_yasg",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "channels",
    "modeltrans",
    "debug_toolbar",
    "easy_thumbnails",
    "fcm_django",
    "django_cleanup",
    # Приложения
    "address",
    "api",
    "banner",
    "bot",
    "common",
    "courier",
    "institution",
    "order",
    "order.feedback",
    "order.promo_codes",
    "payme",
    "product",
    "payment",
    "stories",
    "ofd",
    "user",
    "rkeeper",
    "django_celery_beat"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "tuktuk.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "templates.context_processors.websocket_url",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql_psycopg2"),
        "NAME": os.getenv("DB_NAME", "tuktuk_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "123"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        'CONN_MAX_AGE': 60, 
    }
}
DISABLE_SERVER_SIDE_CURSORS = True

FCM_DJANGO_SETTINGS = {
    "DEVICE_MODEL": "user.CustomFCMDevice",
}

class TelegramHandler(logging.Handler):
    def emit(self, record):
        try:
            TOKEN = os.getenv("BOT_TOKEN")
            CHAT_ID = os.getenv("TELEGRAM_GROUP_ID")
            message = self.format(record)

            if record.exc_info:
                exc_message = ''.join(traceback.format_exception(*record.exc_info))  # traceback to'liq olish
                message += f"\n\nTraceback:\n{exc_message}"  # traceback xabarni qo'shish
                
            url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
            
            payload = {'chat_id': CHAT_ID, 'text': message}
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Error sending message to Telegram: {e}")


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '{levelname} {asctime} {module} {message} {exc_info}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',  # You can adjust this if needed
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'telegram': {
            'level': 'ERROR',
            'class': 'tuktuk.settings.TelegramHandler',
            'formatter': 'detailed',
        },
    },
    'loggers': {
        '': {
            'handlers': ['telegram', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django': {
            'handlers': ['telegram', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
        
WSGI_APPLICATION = "tuktuk.wsgi.application"

AUTH_USER_MODEL = "user.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SESSION_COOKIE_HTTPONLY = False

LANGUAGE_CODE = "ru"
LANGUAGES = (("ru", "Russian"), ("uz", "Uzbek"), ("en", "English"))

TIME_ZONE = "Asia/Tashkent"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "EXCEPTION_HANDLER": "core.exception_handlers.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "rest_framework_gis.schema.GeoFeatureAutoSchema",
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    "PAGE_SIZE": 100,
}

INTERNAL_IPS = [
    "127.0.0.1",
]

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=300),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=300),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=300),
    "SLIDING_TOKEN_LIFETIME": timedelta(days=300),
    "SLIDING_TOKEN_REFRESH_LIFETIME_LATE_USER": timedelta(days=300),
    "SLIDING_TOKEN_LIFETIME_LATE_USER": timedelta(days=300),
    "TOKEN_OBTAIN_SERIALIZER": "crm.api.user.serializers.CustomTokenObtainSerializer",
}

# LOGOUT_REDIRECT_URL = '/index/'

PLAY_MOBILE_SETTINGS = {
    "API_URL": os.getenv("PLAY_MOBILE_API_URL"),
    "LOGIN": os.getenv("PLAY_MOBILE_LOGIN"),
    "PASSWORD": os.getenv("PLAY_MOBILE_PASSWORD"),
    "PREFIX": "Tuktuk express",  # example : abc - Organization name. no more 20 characters.
    "ORIGINATOR": os.getenv(
        "PLAY_MOBILE_NICKNAME"
    ),  # if this field is empty default 3700 or set your originator name
}

THUMBNAIL_ALIASES = {
    "": {
        "big": {"size": (1200, 1200)},
        "small": {"size": (1000, 600)},
        "logo": {"size": (200, 200)},
    }
}

PHONE_NUMBER_REGEX_PATTERN = "^([+]998)([0-9]{9})$"

MAPBOX_ACCESS_TOKEN = "pk.eyJ1IjoiZGFsZXJ6YWZhcm92aWNoIiwiYSI6ImNsMjR0aWg5YjAwbnYzYm11cmxpbnFlYWcifQ.O_feU3l-fa8V8LHcmYIqgg"

ASGI_APPLICATION = "tuktuk.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST"), os.getenv("REDIS_PORT"))],
        },
    },
}

# Redis broker
CELERY_BROKER_URL = f'redis://{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}/0'
CELERY_RESULT_BACKEND = f'redis://{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

PAYME_SETTINGS = {
    "api_url": os.getenv("PAYME_URL"),
    "merchant_id": os.getenv("PAYME_MERCHANT_ID"),
    "key": os.getenv("PAYME_KEY"),
}
PAYME_TEST = {
    "api_url": os.getenv("PAYME_TEST_URL"),
    "merchant_id": os.getenv("PAYME_TEST_MERCHANT_ID"),
    "key": os.getenv("PAYME_KEY"),
}

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# FCM
FIREBASE_APP = initialize_app()

# GNK
DELIVERY_SPIC = os.getenv("DELIVERY_SPIC")
STIR = os.getenv("STIR")
DELIVERY_PACKAGE_CODE = os.getenv("DELIVERY_PACKAGE_CODE")
GNK_INTEGRATION_AVAILABLE = os.getenv("GNK_INTEGRATION_AVAILABLE")
OFD_URL = os.getenv("OFD_URL")
OFD_CERT = os.getenv("OFD_CERT")


# postgis
GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH")
GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH")


