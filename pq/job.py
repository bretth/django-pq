import importlib
import inspect

import times
from picklefield.fields import PickledObjectField
from django.db import models
from json_field import JSONField

class Job(models.Model):

    QUEUED = 1
    FINISHED = 2
    FAILED = 3
    STARTED = 4

    STATUS_CHOICES = (
        (QUEUED, 'queued'),
        (FINISHED, 'finished'),
        (FAILED, 'failed'),
        (STARTED, 'started'),
    )
    connection = None
    created_at = models.DateTimeField()
    origin = models.CharField(max_length=254, null=True, blank=True)
    queue = models.ForeignKey('Queue', null=True, blank=True)
    instance = PickledObjectField(null=True, blank=True)
    func_name = models.CharField(max_length=254)
    args = PickledObjectField(blank=True)
    kwargs = PickledObjectField(blank=True)
    description = models.CharField(max_length=254)
    result_ttl = models.PositiveIntegerField(null=True, blank=True)
    status = models.PositiveIntegerField(null=True, blank=True)
    enqueued_at = models.DateTimeField(null=True, blank=True)
    ended_at =  models.DateTimeField(null=True, blank=True)
    result = PickledObjectField()
    exc_info = models.TextField(null=True, blank=True)
    timeout = models.PositiveIntegerField(null=True, blank=True)
    meta = PickledObjectField(blank=True)

    @classmethod
    def create(cls, func, args=None, kwargs=None, connection=None,
               result_ttl=None, status=None):
        """Creates a new Job instance for the given function, arguments, and
        keyword arguments.
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        assert isinstance(args, tuple), '%r is not a valid args list.' % (args,)
        assert isinstance(kwargs, dict), '%r is not a valid kwargs dict.' % (kwargs,)
        job = cls()
        job.connection = connection
        job.created_at = times.now()
        if inspect.ismethod(func):
            job.instance = func.im_self
            job.func_name = func.__name__
        elif inspect.isfunction(func) or inspect.isbuiltin(func):
            job.func_name = '%s.%s' % (func.__module__, func.__name__)
        else:  # we expect a string
            job.func_name = func
        job.args = args
        job.kwargs = kwargs
        job.description = job.get_call_string()
        job.result_ttl = result_ttl
        job.status = status
        return job

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        if self.instance:
            return getattr(self.instance, func_name)

        module_name, func_name = func_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)

    # Representation
    def get_call_string(self):  # noqa
        """Returns a string representation of the call, formatted as a regular
        Python function invocation statement.
        """
        #if self.func_name is None:
        #    return None

        arg_list = [repr(arg) for arg in self.args]
        arg_list += ['%s=%r' % (k, v) for k, v in self.kwargs.items()]
        args = ', '.join(arg_list)
        return '%s(%s)' % (self.func_name, args)

    # Job execution
    def perform(self):  # noqa
        """Invokes the job function with the job arguments."""
        self.result = self.func(*self.args, **self.kwargs)
        return self.result

    def save(self, *args, **kwargs):
        kwargs.setdefault('using', self.connection)
        super(Job, self).save(*args, **kwargs)

