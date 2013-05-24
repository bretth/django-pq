import time
import multiprocessing
from datetime import datetime, timedelta
from django.utils.timezone import utc, now
from django.test import TestCase, TransactionTestCase
from nose2.tools import params

from pq import Queue
from pq.queue import Queue as PQ
from pq.queue import FailedQueue, get_failed_queue
from pq.job import Job
from pq.worker import Worker
from pq.exceptions import DequeueTimeout, InvalidQueueName


from .fixtures import (say_hello, Calculator,
    div_by_zero, some_calculation, do_nothing)



class TestQueueCreation(TestCase):

    def test_default_queue_create(self):
        queue = Queue()
        self.assertEqual(queue.name, 'default')


class TestQueueNameValidation(TestCase):

    def test_validated_name(self):
        with self.assertRaises(InvalidQueueName):
            PQ.validated_name('failed')


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
        self.q.save()
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
        self.assertEqual(sorted(PQ.all()), sorted([get_failed_queue()]))  # noqa
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
        Queue('fake').save()
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


class TestEnqueueAsyncFalse(TestCase):
    def setUp(self):
        self.q = Queue()

    def test_enqueue_async_false(self):
        job = self.q.enqueue(some_calculation, args=(2, 3), async=False)
        self.assertEqual(job.result, 6)

    def test_enqueue_call_async_false(self):
        job = self.q.enqueue_call(some_calculation, args=(2, 3), async=False)
        self.assertEqual(job.result, 6)

    def test_schedule_call_async_false(self):
        job = self.q.enqueue_call(some_calculation, args=(2, 3), async=False)
        self.assertEqual(job.result, 6)



class TestDeleteExpiredTTL(TransactionTestCase):
    def setUp(self):
        q = Queue()
        q.enqueue(say_hello, kwargs={'name':'bob'}, result_ttl=1)  # expires
        q.enqueue(say_hello, kwargs={'name':'polly'})  # won't expire in this test lifecycle
        q.enqueue(say_hello, kwargs={'name':'frank'}, result_ttl=-1) # never expires
        w = Worker.create([q])
        w.work(burst=True)
        q.enqueue(say_hello, kwargs={'name':'david'}) # hasn't run yet
        self.q = q

    def test_delete_expired_ttl(self):
        time.sleep(1)
        self.q.delete_expired_ttl()
        jobs = Job.objects.all()[:]
        self.assertEqual(len(jobs), 3)


class TestDequeueTimeout(TransactionTestCase):
    def setUp(self):
        q = Queue()
        self.q = q

    def test_dequeue_timeout(self):
        with self.assertRaises(DequeueTimeout):
            PQ.dequeue_any([self.q], timeout=1)


class TestListen(TransactionTestCase):

    def test_listen(self):
        """Postgresql LISTEN on channel with default connection"""

        conn = PQ.listen('default', ['default'])
        self.assertIsNotNone(conn)

class TestNotify(TransactionTestCase):
    def setUp(self):
        self.q = Queue()

    def test_notify(self):
        """Postgresql NOTIFY on channel with default connection"""
        self.q.notify(1)


class TestListenForJobs(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        # pre-call this so we don't need to use multi-process
        # otherwise this is called within the classmethod
        PQ.listen('default', ['default'])
        # Fire off a notification of a fake job enqueued
        self.q.notify(1)

    def test_listen_for_jobs(self):
        """Test the first part of the _listen_for_jobs method which polls
        for notifications"""
        queue_name = PQ._listen_for_jobs(['default'], 'default', 1)
        self.assertEqual('default', queue_name)


class TestListenForJobsSelect(TransactionTestCase):

    def setUp(self):
        # We'll have to simulate the notify method since there are issues with
        # sharing database connections with the additional process
        def fake_job():
            import psycopg2
            import psycopg2.extensions
            time.sleep(1)
            conn = psycopg2.connect("dbname=test_django-pq host=localhost user=django-pq")
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            curs = conn.cursor()
            # fake notifying a job_id 2 has been enqueued on the farq
            curs.execute("SELECT pg_notify(%s, %s);", ('farq', str(2)))

        p = multiprocessing.Process(target=fake_job)
        p.start()


    def test_listen_for_jobs_select(self):
        """Test the 2nd part of the _listen_for_jobs method which
        blocks and waits for postgresql to notify it"""
        queue_name = PQ._listen_for_jobs(['default', 'farq'], 'default', 5)
        self.assertEqual('farq', queue_name)


class TestScheduleJobs(TransactionTestCase):

    def setUp(self):
        self.q = Queue(scheduled=True)
        self.w = Worker.create([self.q])

    def test_shedule_call(self):
        """Schedule to fire now"""
        job = self.q.schedule_call(now(), do_nothing)
        self.w.work(burst=True)
        with self.assertRaises(Job.DoesNotExist) as exc:
            Job.objects.get(queue_id='default', pk=job.id)

    def test_schedule_future_call(self):
        """Schedule to fire in the distant future"""
        job = self.q.schedule_call(datetime(2999,12,1, tzinfo=utc), do_nothing)
        self.w.work(burst=True)
        # check it is still in the queue
        self.assertIsNotNone(Job.objects.get(queue_id='default', pk=job.id))

class TestEnqueueNext(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.job = Job.create(func=some_calculation,
            args=(3, 4),
            kwargs=dict(z=2),
            repeat=1,
            interval=60)
        self.job.save()

    def test_enqueue_next(self):
        """Schedule the next job"""
        job = self.q.enqueue_next(self.job)
        self.assertIsNotNone(job.id)
        self.assertNotEqual(job.id, self.job.id)
        self.assertEqual(job.scheduled_for,
            self.job.scheduled_for + self.job.interval)

    def test_schedule_repeat_infinity(self):
        """Schedule repeats for infinity"""
        self.job.repeat = -1
        job = self.q.enqueue_next(self.job)
        self.assertIsNotNone(job.id)
        self.assertNotEqual(job.id, self.job.id)
        self.assertEqual(job.repeat, self.job.repeat)

    def test_schedule_repeat_until(self):
        """Schedule repeat until datetime"""
        self.job.repeat = datetime(2999,1,1, tzinfo=utc)
        job = self.q.enqueue_next(self.job)
        self.assertIsNotNone(job.id)
        self.assertNotEqual(job.id, self.job.id)
        self.assertEqual(job.repeat, self.job.repeat)
