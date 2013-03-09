
from django.db import models


class Queue(models.Model):

    name = models.CharField(max_length=100, primary_key=True, default='default')
    default_timeout = models.PositiveIntegerField(null=True, blank=True)
    _async = True

    @classmethod
    def create(cls,
               name='default', default_timeout=None,
               connection='default', async=True):
        """Returns a Queue ready for accepting jobs"""
        queue, created = cls.objects.using(connection).get_or_create(
            name='default', defaults={'default_timeout': default_timeout})
        queue._async = async

        return queue
