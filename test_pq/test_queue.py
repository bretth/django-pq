from django.test import TestCase, TransactionTestCase

from pq import Queue
from pq.job import Job
from .fixtures import say_hello

class TestQueueCreation(TransactionTestCase):

    def test_default_queue_create(self):
        queue = Queue()
        self.assertEqual(queue.name, 'default')


class TestQueueInstanceMethods(TransactionTestCase):

    def setUp(self):
        self.q = Queue()

    def test_enqueue(self):  # noqa
        """Enqueueing job onto queues."""

        # say_hello spec holds which queue this is sent to
        job = self.q.enqueue(say_hello, 'Nick', foo='bar')
        self.assertEqual(job.queue, self.q)


class TestEnqueue(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.job = Job.create(func=say_hello, args=('Nick',), kwargs=dict(foo='bar'))


    def test_enqueue_sets_metadata(self):
        """Enqueueing job onto queues modifies meta data."""

        # Preconditions
        self.assertIsNone(self.job.origin)
        self.assertIsNone(self.job.enqueued_at)

        # Action
        self.q.enqueue_job(self.job)

        # Postconditions
        self.assertEquals(self.job.origin, self.q.name)
        self.assertIsNotNone(self.job.enqueued_at)


class TestPopJobOnEmpty(TransactionTestCase):

    def setUp(self):
        self.q = Queue()

    def test_pop_job_on_empty(self):
        job = self.q.pop_job()
        self.assertIsNone(job)


class TestPopJob(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.job = Job.create(func=say_hello, args=('Nick',), kwargs=dict(foo='bar'))
        self.q.enqueue_job(self.job)

    def test_pop_job(self):
        job = self.q.pop_job()
        self.assertEqual(job.func_name, u'test_pq.fixtures.say_hello')

