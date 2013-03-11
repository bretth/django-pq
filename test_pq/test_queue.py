from django.test import TestCase, TransactionTestCase


from pq import Queue
from pq.queue import Queue as PQ
from pq.queue import FailedQueue, get_failed_queue
from pq.job import Job
from .fixtures import say_hello, Calculator, div_by_zero, some_calculation

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


class TestDequeueAnyEmpty(TransactionTestCase):

    def setUp(self):
        self.fooq = Queue('foo')
        self.barq = Queue('bar')

    def test_dequeue_any_empty(self):
        """Fetching work from any given queue."""

        self.assertEquals(PQ.dequeue_any([self.fooq, self.barq], None), None)


class TestDequeueAnySingle(TransactionTestCase):

    def setUp(self):
        self.fooq = Queue('foo')
        self.barq = Queue('bar')
        # Enqueue a single item
        self.barq.enqueue(say_hello)

    def test_dequeue_any_single(self):

        job, queue = PQ.dequeue_any([self.fooq, self.barq], None)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(queue, self.barq)


class TestDequeueAnyMultiple(TransactionTestCase):

    def setUp(self):
        self.fooq = Queue('foo')
        self.barq = Queue('bar')
        # Enqueue items on both queues
        self.barq.enqueue(say_hello, 'for Bar')
        self.fooq.enqueue(say_hello, 'for Foo')

    def test_dequeue_any_multiple(self):

        job, queue = PQ.dequeue_any([self.fooq, self.barq], None)
        self.assertEquals(queue, self.fooq)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, self.fooq.name)
        self.assertEquals(job.args[0], 'for Foo',
                'Foo should be dequeued first.')

        job, queue = PQ.dequeue_any([self.fooq, self.barq], None)
        self.assertEquals(queue, self.barq)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, self.barq.name)
        self.assertEquals(job.args[0], 'for Bar',
                'Bar should be dequeued second.')


class TestGetFailedQueue(TransactionTestCase):
    def test_get_failed_queue(self):
        fq = get_failed_queue()
        self.assertIsInstance(fq, FailedQueue)


class TestFQueueQuarantine(TransactionTestCase):

    def setUp(self):
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.save()
        self.job = job

    def test_quarantine_job(self):
        """Requeueing existing jobs."""

        get_failed_queue().quarantine(self.job, Exception('Some fake error'))  # noqa
        self.assertItemsEqual(PQ.all(), [get_failed_queue()])  # noqa
        self.assertEquals(get_failed_queue().count, 1)


class TestFQueueQuarantineTimeout(TransactionTestCase):

    def setUp(self):
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.timeout = 200
        job.save()
        self.job = job
        self.fq = get_failed_queue()

    def test_quarantine_preserves_timeout(self):
        """Quarantine preserves job timeout."""

        self.fq.quarantine(self.job, Exception('Some fake error'))
        self.assertEquals(self.job.timeout, 200)


class TestRequeue(TransactionTestCase):

    def setUp(self):
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.save()
        self.job = job
        self.fq = get_failed_queue()

    def test_requeue(self):
        self.fq.requeue(self.job.id)
        self.assertEquals(self.fq.count, 0)
        self.assertEquals(Queue('fake').count, 1)


class TestAsyncFalse(TransactionTestCase):
    def test_async_false(self):
     """Executes a job immediately if async=False."""
     q = Queue(async=False)
     job = q.enqueue(some_calculation, args=(2, 3))
     self.assertEqual(job.result, 6)
