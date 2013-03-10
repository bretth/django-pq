from django.test import TestCase, TransactionTestCase

from pq import Queue
from pq.job import Job
from .fixtures import say_hello, Calculator

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


class TestDequeueOnEmpty(TransactionTestCase):

    def setUp(self):
        self.q = Queue()

    def test_pop_job_on_empty(self):
        job = self.q.dequeue()
        self.assertIsNone(job)


class TestDequeue(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.result = self.q.enqueue(say_hello, 'Rick', foo='bar')
        #self.result2 = q.enqueue(c.calculate, 3, 4)
        #self.c = Calculator(2)

    def test_dequeue(self):
        """Dequeueing jobs from queues."""

        # Dequeue a job (not a job ID) off the queue
        self.assertEquals(self.q.count, 1)
        job = self.q.dequeue()
        self.assertEquals(job.id, self.result.id)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, self.q.name)
        self.assertEquals(job.args[0], 'Rick')
        self.assertEquals(job.kwargs['foo'], 'bar')

        # ...and assert the queue count when down
        self.assertEquals(self.q.count, 0)


class TestDequeueInstanceMethods(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.c = Calculator(2)
        self.result = self.q.enqueue(self.c.calculate, 3, 4)


    def test_dequeue_instance_method(self):
        """Dequeueing instance method jobs from queues."""

        job = self.q.dequeue()

        self.assertEquals(job.func.__name__, 'calculate')
        self.assertEquals(job.args, (3, 4))
