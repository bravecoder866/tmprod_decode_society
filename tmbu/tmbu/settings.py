"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""


import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
import logging


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

#load_dotenv(os.path.join(BASE_DIR.parent.parent, '.env'))

DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE", "tmbu.settings")

# LLM API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# Google reCAPTCHA settings
RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY")

#test keys for dev
#RECAPTCHA_PUBLIC_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
#RECAPTCHA_PRIVATE_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'

#Deepgram speech-to-text
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'False').strip().lower() in ['true', '1']
 
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()]

# Session backend (database, file, cache, or signed cookies)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

SESSION_COOKIE_HTTPONLY = True  # Default in Django
SESSION_COOKIE_SECURE = True  # Enabled for production environments
SESSION_COOKIE_SAMESITE = 'Lax'  # 'Lax' or 'Strict' helps mitigate CSRF risks
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_SECURE = True
CSRF_FAILURE_VIEW = 'accounts.views.csrf_failure'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')



# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django_apscheduler',
    'django_recaptcha',
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_celery_results",
    'accounts.apps.AccountsConfig',
    'solutions.apps.SolutionsConfig',
    'payments.apps.PaymentsConfig',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "key": ""
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {
            "access_type": "online",
            "prompt": "select_account"
            },
        "FIELDS": ["email", "username"],
    }
}

# Immediately redirect to Google when the button is clicked
#ACCOUNT_EMAIL_REQUIRED = True
#ACCOUNT_USERNAME_REQUIRED = True

ACCOUNT_SIGNUP_FIELDS = ['email', 'username', 'password1', 'password2']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_SIGNUP_FORM_CLASS = None
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_LOGIN_ERROR_URL = 'social_login_error'
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CustomSocialAccountAdapter"


# Add APScheduler-specific configurations
# APSCHEDULER_AUTOSTART = True  # Start scheduler automatically
# APSCHEDULER_JOBSTORES = {
#    'default': {'type': 'djangoorm', 'tables': ['django_apscheduler_jobstore']},
#}
# APSCHEDULER_EXECUTORS = {
#    'default': {'type': 'thread', 'max_workers': 1},
#}
# APSCHEDULER_JOB_DEFAULTS = {
#    'coalesce': False,
#    'max_instances': 1,
# }
# APSCHEDULER_RUN_NOW_TIMEDELTA = timedelta(seconds=25) 


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Enables language detection
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'solutions.middleware.MilvusMiddleware',
]

LOGOUT_REDIRECT_URL = '/'  # Redirect to home page after logout
LOGIN_REDIRECT_URL = '/'

#for production
CSRF_TRUSTED_ORIGINS = [
    'https://xtembusu.com',
    'https://www.xtembusu.com',
]



# CORS_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []


ROOT_URLCONF = 'tmbu.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'accounts', 'templates'),
            ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tmbu.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
    }
}

# Milvus connection settings
#MILVUS_HOST = os.getenv('MILVUS_HOST', 'milvus-standalone')  # This is the service name defined in docker-compose
#MILVUS_PORT_GRPC = os.getenv('MILVUS_PORT_GRPC', 19530)

# Milvus Standalone Configuration
MILVUS_MODE = os.getenv("MILVUS_MODE")
MILVUS_URI = os.getenv("MILVUS_URI")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN")

# MINIO keys
#MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
#MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")



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


# Email backend for sending emails in Production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

#SMTP settings for your email service provider
EMAIL_HOST = os.getenv('EMAIL_HOST')  # or your email provider's SMTP server
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # Get from environment variable
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # Get from environment variable
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

#LANGUAGES = [
#    ('en', _('English')),
#    ('zh-hans', _('Simplified Chinese')), 
#]

LANGUAGES = [('en', _('English'))]

# Tell Django where to find translations
LOCALE_PATHS = [
    BASE_DIR / 'locale/',
]

USE_I18N = True


USE_L10N = True  # Enables locale-based formatting

USE_TZ = True

TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

#Corekb files path
COREKB_UPLOADS_DIR = os.path.join(BASE_DIR, 'solutions', 'corekb')


#Media
#MEDIA_ROOT=os.path.join(BASE_DIR, 'media')
#MEDIA_URL='/media/'


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Celery settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',  # change to INFO if too verbose
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}