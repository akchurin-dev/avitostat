"""
For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
ENVIRONMENT = os.getenv('ENVIRONMENT')
if ENVIRONMENT == 'DEVELOPMENT':
    DEBUG = True
else:
    DEBUG = False

ALLOWED_HOSTS = ["172.22.0.2", "localhost", "127.0.0.1", "45.12.238.229", "*", "avitostata.ru"]

# Application definition

INSTALLED_APPS = [
    'jet',
    'telegram_bot',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'avito_account',
    'conversion',
    'messaging',
    'deep_tests',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'base.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'base.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASS'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

import os
from pathlib import Path

# Определите BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent
LOCALHOST_IP = os.getenv('LOCALHOST_IP', '127.0.0.1:8000')


# URL для статических файлов
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Путь к директории статических файлов
STATICFILES_DIRS = [
    STATIC_ROOT,
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# for httpS settings
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

#TODO НАСТРОЙКИ БЕЗОПАСНОСТИ после check --deploy
#TODO НАСТРОЙКИ БЕЗОПАСНОСТИ после check --deploy
#TODO НАСТРОЙКИ БЕЗОПАСНОСТИ после check --deploy

CSRF_TRUSTED_ORIGINS = [
    'https://avitostata.ru',
    'https://www.avitostata.ru',
]

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# TODO SENTRY SETTINGS
# TODO SENTRY SETTINGS
# TODO SENTRY SETTINGS

if ENVIRONMENT == 'PRODUCTION':
    import sentry_sdk

    sentry_sdk.init(
        dsn="https://26cd6adb31a7d912277757045055f118@o4506274465972224.ingest.us.sentry.io/4507378908004352",
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'sentry': {
                'level': 'ERROR',
                'class': 'sentry_sdk.integrations.logging.EventHandler',
            },
            'console': {
                'level': 'DEBUG',
                'class': 'sentry_sdk.integrations.logging.EventHandler',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'sentry'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'celery': {
                'handlers': ['console', 'sentry'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }

#TODO django-redis-aiogram sender SETTINGS
#TODO django-redis-aiogram sender SETTINGS
#TODO django-redis-aiogram sender SETTINGS
if ENVIRONMENT == 'PRODUCTION':
    TELEGRAM_BOT = {
        'REDIS_URL': "redis://redis:6379/0",
        'TOKEN': os.getenv('TELEGRAM_BOT_TOKEN_PROD')
    }
else:
    TELEGRAM_BOT = {
        'REDIS_URL': "redis://redis:6379/0",
        'TOKEN': os.getenv('TELEGRAM_BOT_TOKEN')
    }

#TODO CELERY settings
#TODO CELERY settings
#TODO CELERY settings

# Добавляем настройки для Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'


#TODO CELERY_BEAT_SCHEDULE
#TODO CELERY_BEAT_SCHEDULE
#TODO CELERY_BEAT_SCHEDULE
if ENVIRONMENT == 'PRODUCTION':
    CELERY_BEAT_SCHEDULE = {
        'bad_messaging_week_report_task': {
            'task': 'messaging.tasks.bad_messaging_week_report_async_task',
            'schedule': crontab(hour=6, minute=0, day_of_week=5),  # 6 - это суббота (0 - воскресенье, 1 - понедельник и т.д.)
        },
        'bad_messaging_week_report_folder_cleaner_task': {
            'task': 'messaging.tasks.bad_mes_report_pdfs_folder_cleaner_task',
            'schedule': crontab(0, 0, day_of_month='1', month_of_year='1,4,7,10'),
            # Раз в три месяца (1 января, 1 апреля, 1 июля, 1 октября)
        },
    }
else:
    CELERY_BEAT_SCHEDULE = {
        'bad_messaging_week_report_task_DEBUG': {
            'task': 'messaging.tasks.bad_messaging_week_report_async_task',
            'schedule': 100.0,  #  каждые 100 секунд
        },
        # 'bad_messaging_week_report_folder_cleaner_task': {
        #     'task': 'messaging.tasks.bad_mes_report_pdfs_folder_cleaner_task',
        #     'schedule': crontab(0, 0, day_of_month='1', month_of_year='1,4,7,10'),
        #     # Раз в три месяца (1 января, 1 апреля, 1 июля, 1 октября)
        # },
    }

# TODO OTHER THINGS
# TODO OTHER THINGS
# TODO OTHER THINGS
JET_THEMES = [
    {
        'theme': 'default',  # theme folder name
        'color': '#47bac1',  # color of the theme's button in user menu
        'title': 'Default'  # theme title
    },
    {
        'theme': 'green',
        'color': '#44b78b',
        'title': 'Green'
    },
    {
        'theme': 'light-green',
        'color': '#2faa60',
        'title': 'Light Green'
    },
    {
        'theme': 'light-violet',
        'color': '#a464c4',
        'title': 'Light Violet'
    },
    {
        'theme': 'light-blue',
        'color': '#5EADDE',
        'title': 'Light Blue'
    },
    {
        'theme': 'light-gray',
        'color': '#222',
        'title': 'Light Gray'
    }
]
