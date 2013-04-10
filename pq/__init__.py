try:
    __version__ = __import__('pkg_resources').get_distribution('django-pq').version
except:
    __version__ = ''

__all__ = ['__version__', 'Queue', 'SerialQueue', 'Worker', 'Flow']

from django.core.exceptions import ImproperlyConfigured
from .queue import Queue as PQ
from .queue import SerialQueue as SQ
from .worker import Worker as W
from .flow import Flow

Queue = PQ.create
SerialQueue = SQ.create
Worker = W.create
