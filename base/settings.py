import datetime
import os
from pathlib import Path
from typing import Literal

from celery.schedules import crontab, schedule
from dotenv import load_dotenv
from loguru import logger
import pytz
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

ENVIRONMENT_STR = os.getenv('ENVIRONMENT')
ENVIRONMENT: Literal["PRODUCTION", "DEVELOPMENT", "TESTING"] | None

if ENVIRONMENT_STR == "PRODUCTION":
    ENVIRONMENT = "PRODUCTION"
elif ENVIRONMENT_STR == "DEVELOPMENT":
    ENVIRONMENT = "DEVELOPMENT"
elif ENVIRONMENT_STR == "TESTING":
    ENVIRONMENT = "TESTING"
else:
    raise Exception(f"Unexpected ENVIRONMENT value, got {ENVIRONMENT_STR}")

DEBUG = ENVIRONMENT in ["DEVELOPMENT", "TESTING"]

SECRET_KEY = os.getenv('SECRET_KEY')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

AVITO_CLIENT_ID = os.getenv('AVITO_CLIENT_ID')
AVITO_CLIENT_SECRET = os.getenv('AVITO_CLIENT_SECRET')

AVITO_WEBHOOK_HOST = "avitostata.ru"
if DEBUG:
    AVITO_WEBHOOK_HOST = os.getenv('AVITO_WEBHOOK_HOST', '')
    assert AVITO_WEBHOOK_HOST != ''

AVITO_WEBHOOK_URL = f"https://{AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"

AVITOSTATA_ALIVE_BOT_TOKEN = os.getenv("AVITOSTATA_ALIVE_BOT_TOKEN", "")
AVITOSTATA_ALIVE_REPORTS_CHAT_ID = os.getenv("AVITOSTATA_ALIVE_REPORTS_CHAT_ID", "")

OPENAI_SECRET_KEY = os.getenv('OPENAI_SECRET_KEY')

YOOKASSA_TEST_SHOP_ID = os.getenv('YOOKASSA_TEST_SHOP_ID')
YOOKASSA_TEST_SECRET_KEY = os.getenv('YOOKASSA_TEST_SECRET_KEY')

YOOKASSA_PROD_SHOP_ID = os.getenv('YOOKASSA_PROD_SHOP_ID')
YOOKASSA_PROD_SECRET_KEY = os.getenv('YOOKASSA_PROD_SECRET_KEY')

LOCALHOST_IP = os.getenv('LOCALHOST_IP', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_BOT_TOKEN_PROD = os.getenv('TELEGRAM_BOT_TOKEN_PROD', '')

AMO_INTEGRATION_ID = os.getenv('AMO_INTEGRATION_ID')
AMO_SECRET = os.getenv('AMO_SECRET')
AMO_WEBHOOK_DOMAIN = os.getenv('AMO_WEBHOOK_DOMAIN', "")
AMO_REDIRECT_URI = f"https://{AMO_WEBHOOK_DOMAIN}/amo/oauth"

USE_GPT = True
if DEBUG:
    USE_GPT = False
    USE_GPT = True

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_BASE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# SECURITY WARNING: don't run with debug turned on in production!
ALLOWED_HOSTS = [
    "localhost", "127.0.0.1", "www.avitostata.ru", "avitostata.ru", "45.12.238.229",
    "83.222.22.12",

    #Yookassa webhook
    "185.71.76.0/27", "185.71.77.0/27", "77.75.153.0/25", "77.75.156.11",
    "77.75.156.35", "77.75.154.128/25", "2a02:5180::/32",
]

if DEBUG:
    ALLOWED_HOSTS = ["*"]
    INTERNAL_IPS = [
        'django',
        '0.0.0.0',
        '127.0.0.1',
        'localhost',
    ]

DJANGO_BASE_URL = os.getenv("DJANGO_BASE_URL", "https://localhost:8000")
DJANGO_INNER_API_KEY = os.getenv("DJANGO_INNER_API_KEY", "")

# Application definition

INSTALLED_APPS = [
    'jet',
    'django_extensions',  # shell_plus
    'rangefilter',  # filter by date in admin panel
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
    'payments',
    'chat_bot',
    'amo',
    'chatbottasks',
    'transcriptions',
    'ai_requests',
    'amo_a5client',
    'work_reports',
]

if DEBUG:
    INSTALLED_APPS.extend([
        'debug_toolbar',
    ])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'payments.middleware.UserProfileMiddleware',
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
]

if DEBUG:
    MIDDLEWARE.extend([
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ])

ROOT_URLCONF = 'base.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
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
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# URL для доступа к статическим файлам
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# for httpS settings
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# TODO НАСТРОЙКИ БЕЗОПАСНОСТИ после check --deploy

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

TELEGRAM_BOT = {
    'REDIS_URL': REDIS_BASE_URL + "/0",
    'TOKEN': TELEGRAM_BOT_TOKEN,
    'RAISE_EXCEPTION': True,
}

if ENVIRONMENT == 'PRODUCTION':
    TELEGRAM_BOT['TOKEN'] = TELEGRAM_BOT_TOKEN_PROD

# Добавляем настройки для Celery
CELERY_BROKER_URL = REDIS_BASE_URL + "/0"
CELERY_RESULT_BACKEND = REDIS_BASE_URL + "/1"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

if ENVIRONMENT == 'PRODUCTION':
    CELERY_BEAT_SCHEDULE = {
        'bad_messaging_week_report_task': {
            'task': 'messaging.tasks.bad_messaging_week_report_async_task_auto_generated',
            'schedule': crontab(hour='6', minute='0', day_of_week='5'),
        },

        'send_text_report_all_async_task': {
            'task': 'conversion.tasks.send_text_report_all_async_task_auto_generated',
            'schedule': crontab(day_of_week='mon', hour='10', minute='0'),
        },

        'month_report_for_api_generation_task': {
            'task': 'messaging.tasks.month_report_json_getting',
            "schedule": crontab('0', '0', day_of_month='1'),
        },

        'balance_alert_send_task': {
            'task': 'avito_account.tasks.balance_alert_send_task',
            'schedule': schedule(run_every=datetime.timedelta(days=3)),
        },

        'bad_messaging_week_report_folder_cleaner_task': {
            'task': 'messaging.tasks.bad_mes_report_pdfs_folder_cleaner_task',
            'schedule': crontab('0', '0', day_of_month='1', month_of_year='1,4,7,10'),
            # Раз в три месяца (1 января, 1 апреля, 1 июля, 1 октября)
        },

        'db_auto_creator_task': {
            'task': 'messaging.tasks.db_backup_auto_creator_task',
            'schedule': crontab(hour='0', minute='0'),
        },

        'avito_account_tokens_update_task': {
            'task': 'avito_account.tasks.update_tokens',
            'schedule': crontab(hour='2', minute='0'),
        },

        'chat_bot_daily_report_task': {
            'task': 'chat_bot.tasks.statistics_sender_main_task',
            'schedule': crontab(hour='6', minute='0'),
        },
        'daily_work_report': {
            'task': 'work_reports.tasks.send_daily_report',
            'schedule': crontab(hour='6', minute='0'),
        },
        'weekly_work_report': {
            'task': 'work_reports.tasks.send_weekly_report',
            'schedule': crontab(hour='6', minute='30', day_of_week='5'),
        },
        'monthly_work_report': {
            'task': 'work_reports.tasks.send_report_for_last_30_days',
            'schedule': crontab(day_of_month='1', hour='6', minute='0')
        },
        'avito_webhook_subscription_actializing': {
            'task': 'avito_account.tasks.actualize_avito_webhooks_subscriptions',
            'schedule': crontab(hour='*/1', minute='0'),
        },
        'avito_items_actualizing': {
            'task': 'avito_account.tasks.actualize_avito_items',
            'schedule': crontab(hour='0', minute='0'),
        },
        'amo_fields_actualizing': {
            'task': 'amo.tasks.actualize_amo_fields',
            'schedule': crontab(hour='0', minute='0'),
        }
    }
else:
    CELERY_BEAT_SCHEDULE = {
        # 'bad_messaging_week_report_task_auto': {
        #     'task': 'messaging.tasks.bad_messaging_week_report_async_task_auto_generated',
        #     'schedule': 150.0,
        # },
        # 'send_text_report_all_async_task': {
        #     'task': 'conversion.tasks.send_text_report_all_async_task_auto_generated',
        #     'schedule': 100.0,
        # },

        # 'avito_account_tokens_update_task': {
        #     'task': 'avito_account.tasks.update_tokens',
        #     'schedule': crontab(hour=6, minute=19),
        # },
        #
        'chat_bot_daily_report_task_DEBUG': {
            'task': 'chat_bot.tasks.statistics_sender_main_task',
            'schedule': 20,
        },
        # 'chat_bot_daily_report_task': {
        #     'task': 'chat_bot.ChatBotDailyReport.report_sender_via_celery',
        #     'schedule': crontab(hour=6, minute=0),  # Ежедневно в 11:00 утра
        # },
        # 'bad_messaging_week_report_folder_cleaner_task': {
        #     'task': 'messaging.tasks.bad_mes_report_pdfs_folder_cleaner_task',
        #     'schedule': crontab(0, 0, day_of_month='1', month_of_year='1,4,7,10'),
        #     # Раз в три месяца (1 января, 1 апреля, 1 июля, 1 октября)
        # },
        'avito_webhook_subscription_actializing': {
            'task': 'avito_account.tasks.actualize_avito_webhooks_subscriptions',
            'schedule': crontab(minute='*/1'),
        },
        'avito_items_actualizing': {
            'task': 'avito_account.tasks.actualize_avito_items',
            'schedule': crontab(minute='*/1'),
        },
    }

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

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'class': 'logging.StreamHandler',
#             'formatter': 'verbose',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#         'django.server': {
#             'handlers': ['console'],
#             'level': 'INFO',
#             'propagate': False,
#         },
#         'django.request': {
#             'handlers': ['console'],
#             'level': 'INFO',
#             'propagate': False,
#         },
#         'django.db.backends': {
#             'handlers': ['console'],
#             'level': 'ERROR',  # Установите INFO или DEBUG для вывода SQL-запросов
#             'propagate': False,
#         },
#     },
# }

# if ENVIRONMENT == "PRODUCTION":
#     ROLLBAR = {
#         'access_token': '06396e526449412989870a8288788895',
#         'environment': 'development' if DEBUG else 'production',
#         'code_version': '1.0',
#         'root': BASE_DIR,
#     }

if ENVIRONMENT == "PRODUCTION":
    import sentry_sdk

    sentry_sdk.init(
        dsn="https://6fdceed32f06059808466aeb9a7b1e99@o4507288745148416.ingest.us.sentry.io/4508728257871872",
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=1.0,
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )