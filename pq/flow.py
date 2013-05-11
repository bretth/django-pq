from collections import OrderedDict
import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils.timezone import now
from picklefield.fields import PickledObjectField
from six import integer_types

from .queue import Queue
from .job import Job

PQ_DEFAULT_JOB_TIMEOUT = getattr(settings, 'PQ_DEFAULT_JOB_TIMEOUT', 180)

class FlowQueue(Queue):
    class Meta:
        proxy = True

    def enqueue_job(self, job, timeout=None, set_meta_data=True, async=True):
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
            try:
                prior_job = self.jobs.values()[-1]
            except TypeError:  # py33
                prior_job = self.jobs.popitem()[1]
            prior_job.if_result = job.uuid
            self.jobs[prior_job.uuid] = prior_job
        else:  # first job
            job.queue_id = self.name

        self.jobs[job.uuid] = job

        return job


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

    name = models.CharField(max_length=100, default='')
    queue = models.ForeignKey('Queue', blank=True, null=True)
    enqueued_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField('expires', null=True, blank=True)
    status = models.PositiveIntegerField(null=True,
            blank=True, choices=STATUS_CHOICES)
    jobs = PickledObjectField(blank=True)

    class Meta:
        verbose_name ='flow'
        verbose_name_plural = 'flows'


    def __unicode__(self):
        if self.id and self.name:
            return '%i - %s' % (self.id, self.name)
        elif self.id:
            return str(self.id)
        else:
            return self.name

    def enqueue(self, func, *args, **kwargs):
        return self.queue.enqueue(func, *args, **kwargs)

    def enqueue_call(self, func, *args, **kwargs):
        return self.queue.enqueue_call(func, *args, **kwargs)

    def schedule(self, *args, **kwargs):
        return self.queue.schedule(*args, **kwargs)

    def schedule_call(self, *args, **kwargs):
        return self.queue.schedule_call(*args, **kwargs)


    @classmethod
    def delete_expired_ttl(cls, connection):
        """Delete jobs from the queue which have expired"""
        with transaction.commit_on_success(using=connection):
            FlowStore.objects.using(connection).filter(
               status=FlowStore.FINISHED, expired_at__lte=now()).delete()

    def save(self, *args, **kwargs):
        self.queue.save_queue()
        super(FlowStore, self).save(*args, **kwargs)

class Flow(object):

    def __init__(self, queue, name=''):
        queue = FlowQueue.create(name=queue.name)
        self.flowstore = FlowStore(name=name)
        self.flowstore.jobs = []
        self.flowstore.queue = queue
        self.flowstore.save()
        queue.jobs = OrderedDict()
        self.queue = queue
        self.name = name
        self.async = queue._async

    def __enter__(self):
        return self.flowstore

    def __exit__(self, type, value, traceback):
        for i, job in enumerate(self.queue.jobs.values()):
            job.flow = self.flowstore
            if not job.queue_id:
                job.status = Job.FLOW
            else:
                job.status = Job.QUEUED
            if self.async:
                job.save()
                if i == 0:
                    self.flowstore.enqueued_at = job.enqueued_at
                self.flowstore.jobs.append(job.id)
                if job.queue_id:
                    self.queue.notify(job.id)
            else:
                job.perform()
                job.save()

        if self.async and self.queue.jobs:
            self.flowstore.status = FlowStore.QUEUED
            self.flowstore.save()

    @classmethod
    def get(cls, id_or_name):
        if isinstance(id_or_name, integer_types):
            return FlowStore.objects.get(pk=id_or_name)
        else:
            return FlowStore.objects.filter(name=id_or_name)



    @classmethod
    def handle_result(cls, job, queue):
        """Get the next job in the flow sequence"""
        if job.if_result:
            next_job = Job.objects.get(uuid=job.if_result)
            next_job.queue_id = queue.name
            next_job.enqueued_at = now()
            next_job.status = Job.QUEUED
            next_job.save()
            queue.notify(next_job.id)
        else:  # maybe last job
            fs = FlowStore.objects.get(pk=job.flow_id)
            if fs.jobs[-1] == job.id and job.expired_at < now():
                fs.delete()
            elif fs.jobs[-1] == job.id:
                fs.ended_at = job.ended_at
                fs.expired_at = job.expired_at
                fs.status = FlowStore.FINISHED
                fs.save()

    @classmethod
    def handle_failed(cls, job, queue):
        """Handle a failed job"""
        if job.if_failed:
            next_job = Job.objects.get(uuid=job.if_failed)
            next_job.queue_id = queue.name
            next_job.enqueued_at = now()
            next_job.status = Job.QUEUED
            next_job.save()
            queue.notify(next_job.id)
        fs = FlowStore.objects.get(pk=job.flow_id)
        fs.status = FlowStore.FAILED
        fs.save()
