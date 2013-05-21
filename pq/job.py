import importlib
import inspect
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta, weekday
from dateutil.relativedelta import weekdays as wdays
from picklefield.fields import PickledObjectField
from django.db import models
from django.db import transaction
from django.utils.timezone import now
from six import get_method_self, integer_types

from .exceptions import InvalidInterval


class Job(models.Model):

    SCHEDULED = 0
    QUEUED = 1
    FINISHED = 2
    FAILED = 3
    STARTED = 4
    FLOW = 5

    STATUS_CHOICES = (
        (SCHEDULED, 'scheduled'),
        (QUEUED, 'queued'),
        (FINISHED, 'finished'),
        (FAILED, 'failed'),
        (STARTED, 'started'),
        (FLOW, 'flow'),
    )
    uuid = models.CharField(max_length=64, null=True, blank=True)
    connection = None
    created_at = models.DateTimeField()
    origin = models.CharField(max_length=254, null=True, blank=True)
    queue = models.ForeignKey('Queue', null=True, blank=True)
    instance = PickledObjectField(null=True, blank=True)
    func_name = models.CharField(max_length=254)
    args = PickledObjectField(blank=True)
    kwargs = PickledObjectField(blank=True)
    description = models.CharField(max_length=254)
    result_ttl = models.IntegerField(null=True, blank=True)
    status = models.PositiveIntegerField(null=True,
            blank=True, choices=STATUS_CHOICES)
    enqueued_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField()
    repeat = PickledObjectField(null=True, blank=True,
            help_text="Number of times to repeat. -1 for forever.")
    interval = PickledObjectField(null=True, blank=True,
            help_text="Timedelta till next job")
    between = models.CharField(max_length=5, null=True, blank=True)
    weekdays = PickledObjectField(blank=True, null=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField('expires', null=True, blank=True)
    result = PickledObjectField(null=True, blank=True)
    exc_info = models.TextField(null=True, blank=True)
    timeout = models.PositiveIntegerField(null=True, blank=True)
    meta = PickledObjectField(blank=True)
    flow = models.ForeignKey('FlowStore', null=True, blank=True)
    if_failed = models.CharField(max_length=64, null=True, blank=True)
    if_result = models.CharField(max_length=64, null=True, blank=True)

    def __unicode__(self):
        return self.get_call_string()

    @classmethod
    def create(cls, func, args=None,
               kwargs=None, connection=None,
               result_ttl=None, status=None,
               scheduled_for=None, interval=0,
               repeat=0, between=None, weekdays=None):
        """Creates a new Job instance for the given function, arguments, and
        keyword arguments.
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        assert isinstance(args, tuple), \
            '%r is not a valid args list.' % (args,)
        assert isinstance(kwargs, dict), \
            '%r is not a valid kwargs dict.' % (kwargs,)
        job = cls()
        job.connection = connection
        job.created_at = now()
        if inspect.ismethod(func):
            job.instance = get_method_self(func)
            job.func_name = func.__name__
        elif inspect.isfunction(func) or inspect.isbuiltin(func):
            job.func_name = '%s.%s' % (func.__module__, func.__name__)
        else:  # we expect a string
            job.func_name = func
        job.args = args
        job.kwargs = kwargs
        job.description = job.get_call_string()[:254]
        job.result_ttl = result_ttl
        job.status = status
        job.scheduled_for = scheduled_for
        job.interval = interval
        job.between = between
        job.repeat = repeat
        job.weekdays = weekdays
        job.clean()
        return job

    def clean(self):
        if isinstance(self.interval, int) and self.interval >= 0:
                self.interval = relativedelta(seconds=self.interval)
        elif self.scheduled_for and not (
                isinstance(self.interval, timedelta) or
                isinstance(self.interval, relativedelta)):
            raise InvalidInterval(
                "Interval must be a positive integer,"
                " timedelta, or relativedelta instance")

    @classmethod
    def _get_job_or_promise(cls, conn, queue, timeout):
        """
        Helper function that pops the job from the queue
        or returns a queue_name (the promise) and a revised timeout.

        The job is considered started at this point.

        The promised queue name is a queue to be polled
        at the timeout.
        """
        promise = None
        with transaction.commit_on_success(using=conn):
            try:
                qs = cls.objects.using(conn).select_for_update().filter(
                    queue_id=queue.name)
                if queue.scheduled:
                    near_future = now()
                    if timeout:
                        near_future += timedelta(seconds=timeout)
                    job = qs.filter(scheduled_for__lte=near_future).order_by(
                        'scheduled_for')[0]
                    if job.scheduled_for > now():
                        # ensure the next listen times-out
                        # when scheduled job is due
                        timed = near_future - now()
                        if timed.seconds > 1:
                            timeout = timed.seconds
                            promise = job.queue_id
                            job = None
                else:
                    job = qs.order_by('id')[0]

                if job:
                    job.queue = None
                    job.status = Job.STARTED
                    job.save()
                    return job, None, timeout
            except IndexError:
                pass
        return None, promise, timeout

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


    def get_schedule_options(self):
        """Humanized schedule options"""
        s = []
        if isinstance(self.repeat, integer_types) and self.repeat < 0:
            s.append('repeat forever')
        elif isinstance(self.repeat, integer_types) and self.repeat > 0:
            s.append('repeat %i times' % self.repeat)
        elif isinstance(self.repeat, datetime):
            s.append('repeat until %s,' % self.repeat.isoformat()[:16])

        if self.interval and \
            (isinstance(self.interval, relativedelta) or \
            isinstance(self.interval, timedelta)) \
            and self.interval.seconds > 0:
            s.append('every %s' % str(self.interval))

        if self.between:
            s.append('between %s' % self.between)
        if self.weekdays:
            s.append('on any')
            for day in self.weekdays:
                if isinstance(day, weekday):
                    s.append('%s,' % str(day))
                else:
                    s.append('%s,' % str(wdays[day]))
        if s:
            s = ' '.join(s)
            if s[-1] == ',':
                s = s[:-1]
            first_letter = s[0].capitalize()
            s = first_letter + s[1:]
            return s
    get_schedule_options.short_description = 'schedule options'


    def get_ttl(self, default_ttl=None):
        """Returns ttl for a job that determines how long a job and its result
        will be persisted. In the future, this method will also be responsible
        for determining ttl for repeated jobs.
        """
        return default_ttl if self.result_ttl is None else self.result_ttl

    # Representation
    def get_call_string(self):  # noqa
        """Returns a string representation of the call, formatted as a regular
        Python function invocation statement.
        """
        if self.func_name is None:
            return 'None'

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
        if not self.enqueued_at:
            self.enqueued_at = now()
        if not self.scheduled_for:
            self.scheduled_for = self.enqueued_at
        super(Job, self).save(*args, **kwargs)


class FailedJob(Job):
    class Meta:
        proxy = True


class QueuedJob(Job):
    class Meta:
        proxy = True


class ScheduledJob(Job):
    class Meta:
        proxy = True


class DequeuedJob(Job):
    class Meta:
        proxy = True
