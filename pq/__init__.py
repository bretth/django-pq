try:
    __version__ = __import__('pkg_resources').get_distribution('django-pq').version
except:
    __version__ = ''

from django.core.exceptions import ImproperlyConfigured
from .queue import Queue as PQ

Queue = PQ.create

