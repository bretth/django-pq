import logging
import select
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta
from django.db import connections, DatabaseError
from django.db import transaction
from django.db import models
from django.conf import settings
from django.utils.timezone import now
from six import string_types

from .job import Job
from .utils import get_restricted_datetime
from .exceptions import DequeueTimeout, InvalidBetween, InvalidInterval

PQ_DEFAULT_JOB_TIMEOUT = getattr(settings, 'PQ_DEFAULT_JOB_TIMEOUT', 180)

logger = logging.getLogger(__name__)

def get_failed_queue(connection='default'):
    """Returns a handle to the special failed queue."""
    return FailedQueue.create(connection=connection)


class _EnqueueArgs(object):
    """Simple argument and keyword argument wrapper
        for enqueue and schedule queue methods
    """
    def __init__(self, *args, **kwargs):
        self.timeout = None
        self.result_ttl = None
        self.args = args
        self.kwargs = kwargs
        # Detect explicit invocations, i.e. of the form:
        #  q.enqueue(foo, args=(1, 2), kwargs={'a': 1}, timeout=30)
        if 'args' in kwargs or 'kwargs' in kwargs:
            assert args == (), 'Extra positional arguments cannot be used when using explicit args and kwargs.'  # noqa
            self.result_ttl = kwargs.pop('result_ttl', None)
            self.timeout = kwargs.pop('timeout', None)
            self.args = kwargs.pop('args', None)
            self.kwargs = kwargs.pop('kwargs', None)


class Queue(models.Model):

    connection = None
    name = models.CharField(max_length=100, primary_key=True, default='default')
    default_timeout = models.PositiveIntegerField(null=True, blank=True)
    cleaned = models.DateTimeField(null=True, blank=True)
    scheduled = models.BooleanField(default=False,
        help_text="Optimisation: scheduled tasks are slower.")
    lock_expires = models.DateTimeField(default=now())
    serial = models.BooleanField(default=False)
    _async = True

    def __unicode__(self):
        return self.name

    @classmethod
    def create(cls,
               name='default', default_timeout=None,
               connection='default', async=True):
        """Returns a Queue ready for accepting jobs"""
        queue, created = cls.objects.using(connection).get_or_create(
            name=name, defaults={'default_timeout': default_timeout})
        queue.connection = connection
        queue._async = async

        return queue


    @classmethod
    def all(cls, connection='default'):
        allqs = []
        queues = cls.objects.using(connection).all()[:]
        for q in queues:
            if q.name == 'failed':
                allqs.append(get_failed_queue(connection))
            else:
                allqs.append(q)

        return allqs


    @property
    def count(self):
        return Job.objects.using(self.connection).filter(queue_id=self.name).count()


    def delete_expired_ttl(self):
        """Delete jobs from the queue which have expired"""
        with transaction.commit_on_success(using=self.connection):
            Job.objects.using(self.connection).filter(
                origin=self.name, status=Job.FINISHED, expired_at__lte=now()).delete()

    def empty(self):
        """Delete all jobs from a queue"""
        Job.objects.using(self.connection).filter(queue_id=self.name).delete()

    def enqueue_next(self, job):
        """Enqueue the next scheduled job relative to this one"""
        if not job.repeat:
            return

        if isinstance(job.repeat, datetime):
            if job.repeat <= now():
                return
            else:
                repeat = job.repeat
        else:
            repeat = job.repeat - 1 if job.repeat > 0 else -1
        timeout = job.timeout
        scheduled_for = job.scheduled_for + job.interval
        scheduled_for = get_restricted_datetime(scheduled_for, job.between, job.weekdays)
        # handle trivial repeats
        if not self.scheduled and (scheduled_for > job.scheduled_for):
            self.scheduled = True
            self.save()
        job = Job.create(job.func, job.args, job.kwargs, connection=job.connection,
                         result_ttl=job.result_ttl,
                         scheduled_for=scheduled_for,
                         repeat=repeat,
                         interval=job.interval,
                         between=job.between,
                         weekdays=job.weekdays,
                         status=Job.QUEUED)
        return self.enqueue_job(job, timeout=timeout)


    def enqueue_call(self, func, args=None, kwargs=None,
        timeout=None, result_ttl=None, at=None,
        repeat=None, interval=0, between='', weekdays=None): #noqa
        """Creates a job to represent the delayed function call and enqueues
        it.

        It is much like `.enqueue()`, except that it takes the function's args
        and kwargs as explicit arguments.  Any kwargs passed to this function
        contain options for PQ itself.
        """
        timeout = timeout or self.default_timeout
        # Scheduled tasks require a slower query
        if at and not self.scheduled:
            self.scheduled = True
            self.save()
        at = get_restricted_datetime(at, between, weekdays)
        job = Job.create(func, args, kwargs, connection=self.connection,
                         result_ttl=result_ttl,
                         scheduled_for=at,
                         repeat=repeat,
                         interval=interval,
                         between=between,
                         weekdays=weekdays,
                         status=Job.QUEUED)
        return self.enqueue_job(job, timeout=timeout)

    def enqueue(self, f, *args, **kwargs):
        """Creates a job to represent the delayed function call and enqueues
        it.

        Expects the function to call, along with the arguments and keyword
        arguments.

        The function argument `f` may be any of the following:

        * A reference to a function
        * A reference to an object's instance method
        * A string, representing the location of a function (must be
          meaningful to the import context of the workers)
        """
        if not isinstance(f, string_types) and f.__module__ == '__main__':
            raise ValueError(
                    'Functions from the __main__ module cannot be processed '
                    'by workers.')
        enq = _EnqueueArgs(*args, **kwargs)

        return self.enqueue_call(func=f, args=enq.args, kwargs=enq.kwargs,
                                 timeout=enq.timeout, result_ttl=enq.result_ttl)

    def enqueue_job(self, job, timeout=None, set_meta_data=True):
        """Enqueues a job for delayed execution.

        When the `timeout` argument is sent, it will overrides the default
        timeout value of 180 seconds.  `timeout` may either be a string or
        integer.

        If the `set_meta_data` argument is `True` (default), it will update
        the properties `origin` and `enqueued_at`.

        If Queue is instantiated with async=False, job is executed immediately.
        """
        if set_meta_data:
            job.origin = self.name

        if timeout:
            job.timeout = timeout
        else:
            job.timeout = PQ_DEFAULT_JOB_TIMEOUT  # default

        if self._async:
            job.queue_id = self.name
            job.save()
            self.notify(job.id)

        else:
            job.perform()
            job.save()
        return job

    def schedule(self, at, f, *args, **kwargs):
        """As per enqueue but schedule ``at`` datetime"""

        if not isinstance(f, string_types) and f.__module__ == '__main__':
            raise ValueError(
                    'Functions from the __main__ module cannot be processed '
                    'by workers.')
        enq = _EnqueueArgs(*args, **kwargs)

        return self.enqueue_call(func=f, args=enq.args, kwargs=enq.kwargs,
                                 timeout=enq.timeout, result_ttl=enq.result_ttl,
                                 at=at)


    def schedule_call(self, at, f, args=None, kwargs=None,
        timeout=None, result_ttl=None, repeat=0, interval=0, between=''):
        """
        As per enqueue_call but friendly positional ``at``
        datetime argument.

        ``repeat`` a number of times or infinitely -1 at
        ``interval`` seconds. Interval also accepts a timedelta or
        dateutil relativedelta instance

        ``between`` is a time window that the scheduled
        function will be called for example:
        '0:0/6:00' or '0-6' or '0.0-6.0'

        """

        return self.enqueue_call(func=f, args=args, kwargs=kwargs,
                                 timeout=timeout, result_ttl=result_ttl,
                                 at=at, repeat=repeat, interval=interval,
                                 between=between)

    def dequeue(self):
        """Dequeues the front-most job from this queue.

        Returns a Job instance, which can be executed or inspected.
        Does not respect serial queue locks
        """
        with transaction.commit_on_success(using=self.connection):
            try:
                job = Job.objects.using(self.connection).select_for_update().filter(
                queue=self, status=Job.QUEUED,
                scheduled_for__lte=now()).order_by('scheduled_for')[0]
                job.queue = None
                job.save()
            except IndexError:
                job = None
        if job and job.repeat:
            self.enqueue_next(job)

        return job


    @classmethod
    def _listen_for_jobs(cls, queue_names, connection_name, timeout):
        """Get notification from postgresql channels
        corresponding to queue names.
        """
        conn = cls.listen(connection_name, queue_names)

        while True:
            for notify in conn.notifies:
                if not notify.channel in queue_names:
                    continue
                conn.notifies.remove(notify)
                logger.debug('Got job notification %s on queue %s'% (
                    notify.payload, notify.channel))
                return notify.channel
            else:
                r, w, e = select.select([conn], [], [], timeout)
                if not (r or w or e):
                    raise DequeueTimeout(timeout)
                logger.debug('Got data on %s' % (str(r[0])))
                conn.poll()

    @classmethod
    def dequeue_any(cls, queues, timeout):
        """Helper method, that polls the database queues for new jobs.
        The timeout parameter is interpreted as follows:
            None - non-blocking (return immediately)
             > 0 - maximum number of seconds to block

        Returns a job instance and a queue
        """
        burst = True if not timeout else False
        job = None
        # queues must share the same connection - enforced at worker startup
        conn = queues[0].connection
        queue_names = [q.name for q in queues]
        q_lookup = dict(zip(queue_names, queues))
        default_timeout = timeout or 0
        queue_stack = queues[:]
        while True:
            while queue_stack:
                q = queue_stack.pop(0)
                if q.serial and not q.acquire_lock(timeout):
                    # promise to check the queue at timeout
                    job = None
                    promise = q.name
                else:
                    job, promise, timeout = Job._get_job_or_promise(
                        conn, q, timeout)
                if job and job.repeat:
                    self.enqueue_next(job)
                if job:
                    return job, q
            if burst:
                return
            if promise:
                queue_stack.append(promise)
            q = cls._listen_for_jobs(queue_names, conn, timeout)
            timeout = default_timeout
            queue_stack.append(q_lookup[q])

    @classmethod
    def listen(cls, connection_name, queue_names):
        conn = connections[connection_name]
        cursor = conn.cursor()
        for q_name in queue_names:
            sql = "LISTEN \"%s\"" % q_name
            cursor.execute(sql)
        cursor.close()
        # Need to return django's wrapped open connection so that
        # the calling method can use the same session to actually
        # receive pg notify messages
        return conn.connection


    def notify(self, job_id):
        """Notify postgresql channel when a job is enqueued"""
        cursor = connections[self.connection].cursor()
        cursor.execute("SELECT pg_notify(%s, %s);", (self.name, str(job_id)))
        cursor.close()


class SerialQueue(Queue):
    """A queue with a lock"""

    class Meta:
        proxy = True

    @classmethod
    def create(cls,
               name='default', default_timeout=None,
               connection='default', async=True):
        """Returns a Queue ready for accepting jobs"""
        queue, created = cls.objects.using(connection).get_or_create(
            name=name, serial=True,
            defaults={'default_timeout': default_timeout})
        queue.connection = connection
        queue._async = async

        return queue

    def acquire_lock(self, timeout=0, no_wait=True):
        try:
            with transaction.commit_on_success(using=self.connection):
                SerialQueue.objects.using(
                    self.connection).select_for_update(
                    no_wait=no_wait).get(
                    name=self.name, lock_expires__lte=now())
                if timeout:
                    self.lock_expires = now() + timedelta(seconds=timeout)
                    self.save()
        except DatabaseError:
            logger.debug('%s SerialQueue currently locked on update' % self.name)
            return False
        except SerialQueue.DoesNotExist:
            logger.debug('%s SerialQueue currently locked' % self.name)
            return False
        return True

    def release_lock(self):
        self.lock_expires = now()
        self.save()


class FailedQueue(Queue):
    class Meta:
        proxy = True

    @classmethod
    def create(cls, connection='default'):
        return super(FailedQueue, cls).create('failed', connection=connection)

    def quarantine(self, job, exc_info):
        """Puts the given Job in quarantine (i.e. put it on the failed
        queue).

        This is different from normal job enqueueing, since certain meta data
        must not be overridden (e.g. `origin` or `enqueued_at`) and other meta
        data must be inserted (`ended_at` and `exc_info`).
        """
        job.ended_at = now()
        job.exc_info = exc_info
        return self.enqueue_job(job, timeout=job.timeout, set_meta_data=False)


    def requeue(self, job_id):
        """Requeues the job with the given job ID."""
        with transaction.commit_on_success(self.connection):
            job = Job.objects.using(self.connection).select_for_update().get(id=job_id)
            # Delete it from the failed queue (raise an error if that failed)
            job.queue = None
            job.status = Job.QUEUED
            job.exc_info = None
            job.scheduled_for = now()
            job.save()
            q = Queue.create(job.origin, connection=self.connection)
            q.enqueue_job(job, timeout=job.timeout)

