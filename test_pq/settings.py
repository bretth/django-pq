import os
try:
    from psycopg2cffi import compat
    compat.register()
except ImportError:
    pass

DEBUG=True
TEMPLATE=DEBUG
USE_TZ = True
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
SOUTH_TESTS_MIGRATE = False
PQ_QUEUE_CACHE = False # switch off for tests

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django-pq',
        'USER': 'django-pq',
        'PASSWORD': 'django-pq',
        'HOST': '127.0.0.1',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': 5432,
        'OPTIONS': {'autocommit': True}
    },

}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'pq',
)
if os.getenv('SOUTH'):
    INSTALLED_APPS += ('south', )

ROOT_URLCONF='test_pq.urls'
SECRET_KEY = '1234'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '[%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':"logging.StreamHandler",
            'formatter': 'standard'
        },
    },
    'loggers': {
        'pq': {
            'handlers': ['console'],
            'level': os.getenv('LOGGING_LEVEL', 'CRITICAL'),
            'propagate': True
        },
    }
}
