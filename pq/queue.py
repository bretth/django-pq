import time
import times

from django.db import transaction
from django.db import models
from django.conf import settings

from .job import Job

PQ_DEFAULT_JOB_TIMEOUT = 180 if not hasattr(
    settings, 'PQ_DEFAULT_JOB_TIMEOUT') else settings.PQ_DEFAULT_JOB_TIMEOUT
PQ_POLL_CYCLE = 60 if not hasattr(
    settings, 'PQ_POLL_CYCLE') else settings.PQ_POLL_CYCLE


class Queue(models.Model):

    connection = None
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
        queue.connection = connection
        queue._async = async

        return queue

    @property
    def count(self):
        return Job.objects.using(self.connection).filter(queue_id=self.name).count()


    def enqueue_call(self, func, args=None, kwargs=None, timeout=None, result_ttl=None): #noqa
        """Creates a job to represent the delayed function call and enqueues
        it.

        It is much like `.enqueue()`, except that it takes the function's args
        and kwargs as explicit arguments.  Any kwargs passed to this function
        contain options for RQ itself.
        """
        timeout = timeout or self.default_timeout
        job = Job.create(func, args, kwargs, connection=self.connection,
                         result_ttl=result_ttl, status=Job.QUEUED)
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
        if not isinstance(f, basestring) and f.__module__ == '__main__':
            raise ValueError(
                    'Functions from the __main__ module cannot be processed '
                    'by workers.')

        # Detect explicit invocations, i.e. of the form:
        #     q.enqueue(foo, args=(1, 2), kwargs={'a': 1}, timeout=30)
        timeout = None
        result_ttl = None
        if 'args' in kwargs or 'kwargs' in kwargs:
            assert args == (), 'Extra positional arguments cannot be used when using explicit args and kwargs.'  # noqa
            timeout = kwargs.pop('timeout', None)
            args = kwargs.pop('args', None)
            result_ttl = kwargs.pop('result_ttl', None)
            kwargs = kwargs.pop('kwargs', None)

        return self.enqueue_call(func=f, args=args, kwargs=kwargs,
                                 timeout=timeout, result_ttl=result_ttl)

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
            job.enqueued_at = times.now()

        if timeout:
            job.timeout = timeout  # _timeout_in_seconds(timeout)
        else:
            job.timeout = PQ_DEFAULT_JOB_TIMEOUT  # default

        if self._async:
            job.queue_id = self.name
            job.status = Job.QUEUED
            job.save()
        else:
            job.perform()
            job.save()
        return job

    def dequeue(self):
        """Dequeues the front-most job from this queue.

        Returns a Job instance, which can be executed or inspected.
        """
        with transaction.commit_on_success(using=self.connection):
            try:
                job = Job.objects.using(self.connection).select_for_update().filter(
                queue=self, status=Job.QUEUED).order_by('-id')[0]
                job.queue = None
                job.save()
            except IndexError:
                job = None

        return job

    @classmethod
    def dequeue_any(cls, queues, timeout):
        """Helper method, that polls the database queues for new jobs.
        The timeout parameter is interpreted as follows:
            None - non-blocking (return immediately)
             > 0 - maximum number of seconds to block

        Returns a job instance and a queue
        """
        if not timeout:
            timeout = 1
        job = None
        while timeout > 0:
            for queue in queues:
                with transaction.commit_on_success(using=queue.connection):
                    try:
                        job = Job.objects.using(queue.connection).select_for_update().filter(
                            queue=queue).order_by('-id')[0]
                        job.queue = None
                        job.save()
                        return job, queue
                    except IndexError:
                        pass
            if timeout > PQ_POLL_CYCLE:
                time.sleep(PQ_POLL_CYCLE)
            timeout -= PQ_POLL_CYCLE
        return

