import os
from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = BASE_DIR / '.env'
# Read .env file for local development when it exists.
if env_file.exists():
    env.read_env(env_file)


def _split_csv(value):
    return [item.strip() for item in value.split(',') if item.strip()]

SECRET_KEY = env('SECRET_KEY', default='django-insecure-gsu687u554r(9kqkg6%9nrnm67%nd=%se_y9i*zrwxchf@94n!')
DEBUG = env.bool('DEBUG', default=False)
default_allowed_hosts = {
    '127.0.0.1',
    'localhost',
    'testserver',
    '.onrender.com',
    'stupup.onrender.com',
    'site-shop-gamma.vercel.app',
    'site-shop-bcqi3qubo-thoufeeq-xz7s-projects.vercel.app',
}
configured_allowed_hosts = set(_split_csv(os.environ.get('ALLOWED_HOSTS', '')))
deployment_hosts = {
    host for host in (os.environ.get('VERCEL_URL'), os.environ.get('RENDER_EXTERNAL_HOSTNAME')) if host
}
ALLOWED_HOSTS = sorted(default_allowed_hosts | configured_allowed_hosts | deployment_hosts)

default_csrf_trusted_origins = {
    'https://stupup.onrender.com',
    'https://site-shop-gamma.vercel.app',
    'https://site-shop-bcqi3qubo-thoufeeq-xz7s-projects.vercel.app',
}
configured_csrf_trusted_origins = set(_split_csv(os.environ.get('CSRF_TRUSTED_ORIGINS', '')))
deployment_origins = {f'https://{host}' for host in deployment_hosts}
CSRF_TRUSTED_ORIGINS = sorted(
    default_csrf_trusted_origins | configured_csrf_trusted_origins | deployment_origins
)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store.apps.StoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecommerce_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce_project.wsgi.application'

database_url = env('DATABASE_URL', default='').strip()
is_vercel = bool(os.environ.get('VERCEL'))

if database_url:
    DATABASES = {
        'default': env.db('DATABASE_URL'),
    }
elif all(
    env(var_name, default='').strip()
    for var_name in ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST']
):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
else:
    if is_vercel:
        raise ImproperlyConfigured(
            'Set DATABASE_URL or the DB_NAME/DB_USER/DB_PASSWORD/DB_HOST env vars in Vercel.'
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

LANGUAGE_CODE = 'en-in'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'hello@stupup.local'
STORE_WHATSAPP_NUMBER = os.environ.get('STORE_WHATSAPP_NUMBER', '918301984387')
ADMIN_DASHBOARD_USERNAME = env('ADMIN_DASHBOARD_USERNAME', default='admin')
ADMIN_DASHBOARD_PASSWORD = env('ADMIN_DASHBOARD_PASSWORD', default='StupUpAdmin@2026')
ADMIN_DASHBOARD_EMAIL = env('ADMIN_DASHBOARD_EMAIL', default='admin@stupup.local')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
