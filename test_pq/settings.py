DEBUG=True
TEMPLATE=DEBUG
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

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
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
    }
}
