from collections import OrderedDict
import uuid

from django.conf import settings
from django.db import models
from django.utils.timezone import now

from .queue import Queue
from .job import Job

PQ_DEFAULT_JOB_TIMEOUT = getattr(settings, 'PQ_DEFAULT_JOB_TIMEOUT', 180)

class FlowQueue(Queue):
    class Meta:
        proxy = True

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

        # set the simple sequential case on success
        job.uuid = uuid.uuid4()
        if self.jobs:
            prior_job = self.jobs.values()[-1]
            prior_job.if_result = job.uuid
            self.jobs[prior_job.uuid] = prior_job
        else:  # first job
            job.queue_id = self.name

        self.jobs[job.uuid] = job

        return job

    def enqueue(self, func, *args, **kwargs):

        return super(FlowQueue, self).enqueue(func, *args, **kwargs)

    def enqueue_call(self, func, *args, **kwargs):

        return super(FlowQueue, self).enqueue_call(func, *args, **kwargs)


    @classmethod
    def handle_success(cls, job):
        pass

    @classmethod
    def handle_failure(cls, job):
        pass


class FlowStore(models.Model):
    """Flow storage """

    QUEUED = 1
    FINISHED = 2
    FAILED = 3

    STATUS_CHOICES = (
        (QUEUED, 'queued'),
        (FINISHED, 'finished'),
        (FAILED, 'failed'),
    )

    name = models.CharField(max_length=100, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField('expires', null=True, blank=True)
    status = models.PositiveIntegerField(null=True,
            blank=True, choices=STATUS_CHOICES)

    class Meta:
        verbose_name ='flow'
        verbose_name_plural = 'flows'


class Flow(object):

    def __init__(self, queue, name='default'):
        queue = FlowQueue.create(name=queue.name)
        queue.jobs = OrderedDict()
        self.queue = queue
        self.name = name
        self.async = queue._async

    def __enter__(self):
        return self.queue

    def __exit__(self, type, value, traceback):
        for job in self.queue.jobs.values():
            if not job.queue_id:
                job.status = Job.FLOW
            if self.async:
                job.save()
                if job.queue_id:
                    self.queue.notify(job.id)
            else:
                job.perform()
                job.save()

    @classmethod
    def handle_result(cls, job, queue):
        """Get the next job in the flow sequence"""
        next_job = Job.objects.get(uuid=job.if_result)
        next_job.queue_id = queue.name
        next_job.enqueued_at = now()
        next_job.status = Job.QUEUED
        next_job.save()
        queue.notify(next_job.id)

    @classmethod
    def handle_failed(cls, job, queue):
        """Handle a failed job"""
        pass



