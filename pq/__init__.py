
from django.core.exceptions import ImproperlyConfigured
try:
    from .queue import Queue as PQ
    Queue = PQ.create
except ImproperlyConfigured:
    pass


