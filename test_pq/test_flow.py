from django.test import TestCase

from pq.flow import Flow, FlowStore
from pq import Queue, Worker
from pq.job import Job
from .fixtures import say_hello, do_nothing

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


class TestFlowPerform(TestCase):

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


class TestFlowStore(TestCase):

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


