import time
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from pq.flow import Flow, FlowStore
from pq import Queue, Worker
from pq.queue import FailedQueue
from pq.job import Job
from .fixtures import say_hello, do_nothing, some_calculation

class TestFlowCreate(TestCase):

    def setUp(self):
        self.q = Queue()

    def test_simple_flow(self):
        with Flow(self.q) as f:
            job = f.enqueue(say_hello, 'Bob')
            n_job = f.enqueue(do_nothing)

        # jobs must be performed in sequence
        self.assertLess(job.id, n_job.id)

        # jobs must have uuids
        self.assertIsNotNone(job.uuid)
        self.assertIsNotNone(n_job.uuid)

        # Job 1 must be queued
        self.assertEqual(job.status, job.QUEUED)
        self.assertEqual('default', job.queue_id)

        # Job 2 must not be queued
        self.assertEqual(n_job.status, job.FLOW)
        self.assertIsNone(n_job.queue_id)


class TestFlowPerform(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q)
        with Flow(self.q) as f:
            self.job = f.enqueue(say_hello, 'Bob')
            self.n_job = f.enqueue(do_nothing)

    def test_flow_perform(self):
        self.w.work(burst=True)
        j1 = Job.objects.get(pk=self.job.id)
        j2 = Job.objects.get(pk=self.n_job.id)
        self.assertEqual(Job.FINISHED, j1.status)
        self.assertEqual(Job.FINISHED, j2.status)
        self.assertEqual(self.q.count, 0)


class TestFlowStore(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q)
        with Flow(self.q, name='test') as f:
            self.job = f.enqueue(say_hello, 'Bob')
            self.n_job = f.enqueue(do_nothing)

    def test_flowstore(self):

        fs = FlowStore.objects.get(name='test')
        j1 = Job.objects.get(pk=self.job.id)
        self.assertEqual(len(fs.jobs), 2)

        self.assertEqual(fs.status, FlowStore.QUEUED)
        self.assertEqual(fs.enqueued_at, j1.enqueued_at)
        self.assertIsNone(fs.ended_at)
        self.assertIsNone(fs.expired_at)

        self.w.work(burst=True)

        fs = FlowStore.objects.get(name='test')
        self.assertEqual(fs.status, FlowStore.FINISHED)
        self.assertIsNotNone(fs.ended_at)
        self.assertIsNotNone(fs.expired_at)


class TestFlowStoreExpiredTTL(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q, default_result_ttl=1)
        with Flow(self.q, name='test') as f:
            self.n_job = f.enqueue(do_nothing)

    def test_delete_expired_ttl(self):
        self.w.work(burst=True)
        self.assertIsNotNone(FlowStore.objects.get(name='test'))
        time.sleep(1)
        self.w.work(burst=True)
        with self.assertRaises(FlowStore.DoesNotExist):
            fs = FlowStore.objects.get(name='test')


class TestFlowStoreExpiredTTLOnDequeue(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q, default_result_ttl=1, default_worker_ttl=2.1, expires_after=1)
        with Flow(self.q, name='test') as f:
            self.n_job = f.enqueue(do_nothing)

    def test_delete_expired_ttl_on_dequeue(self):
        self.w.work()
        with self.assertRaises(FlowStore.DoesNotExist):
            fs = FlowStore.objects.get(name='test')


class TestFlowStoreFailed(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q)
        with Flow(self.q, name='test') as f:
            # enqueue a job to fail
            self.job = f.enqueue(some_calculation, 2, 3, 0)
            self.n_job = f.enqueue(do_nothing)

    def test_flowstore_failed(self):

        fs = FlowStore.objects.get(name='test')
        self.w.work(burst=True)

        fs = FlowStore.objects.get(name='test')
        self.assertEqual(fs.status, FlowStore.FAILED)
        self.assertIsNone(fs.ended_at)
        self.assertIsNone(fs.expired_at)
        n_job = Job.objects.get(pk=self.n_job.id)
        self.assertIsNone(n_job.queue_id)
        self.assertEqual(n_job.status, Job.FLOW)
        job = Job.objects.get(pk=self.job.id)
        # alter the args so it passes
        job.args = (2, 3, 2)
        job.save()
        fq = FailedQueue.create()
        fq.requeue(job.id)

        # do work
        self.w.work(burst=True)

        # should now be finished
        fs = FlowStore.objects.get(name='test')
        self.assertEqual(fs.status, FlowStore.FINISHED)
        job = Job.objects.get(pk=self.job.id)
        n_job = Job.objects.get(pk=self.n_job.id)
        self.assertEqual(job.status, Job.FINISHED)
        self.assertEqual(n_job.status, Job.FINISHED)
