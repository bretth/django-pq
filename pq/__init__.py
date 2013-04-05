try:
    __version__ = __import__('pkg_resources').get_distribution('django-pq').version
except:
    __version__ = ''

from django.core.exceptions import ImproperlyConfigured
from .queue import Queue as PQ
from .queue import SerialQueue as SQ

Queue = PQ.create
SerialQueue = SQ.create

