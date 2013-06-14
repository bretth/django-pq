import os
import time
import times
from datetime import datetime
from django.test import TransactionTestCase, TestCase
from django.utils.timezone import utc
from nose2.tools import params

from pq import Queue
from pq.queue import get_failed_queue
from pq.worker import Worker
from pq.job import Job

from .fixtures import say_hello, div_by_zero, create_file_after_timeout


class TestWorker(TransactionTestCase):
    def setUp(self):
        self.fooq, self.barq = Queue('foo'), Queue('bar')

    def test_create_worker(self):
        """Worker creation."""

        w = Worker.create([self.fooq, self.barq])
        self.assertEquals(w.queues, [self.fooq, self.barq])


class TestWorkNoJobs(TransactionTestCase):
    def setUp(self):
        self.fooq, self.barq = Queue('foo'), Queue('bar')
        self.w = Worker.create([self.fooq, self.barq])

    def test_work_no_jobs(self):
        self.assertEquals(self.w.work(burst=True), False,
                'Did not expect any work on the queue.')


class TestWorkerWithJobs(TransactionTestCase):
    def setUp(self):
        self.fooq, self.barq = Queue('foo'), Queue('bar')
        self.w = Worker.create([self.fooq, self.barq])
        self.fooq.enqueue(say_hello, name='Frank')

    def test_worker_with_jobs(self):

        self.assertEquals(self.w.work(burst=True), True,
                'Expected at least some work done.')


class TestWorkViaStringArg(TransactionTestCase):
    def setUp(self):
        self.q = Queue('foo')
        self.w = Worker.create([self.q])
        self.job = self.q.enqueue('test_pq.fixtures.say_hello', name='Frank')

    def test_work_via_string_argument(self):
        """Worker processes work fed via string arguments."""

        self.assertEquals(self.w.work(burst=True), True,
                'Expected at least some work done.')
        job = Job.objects.get(id=self.job.id)
        self.assertEquals(job.result, 'Hi there, Frank!')

class TestWorkIsUnreadable(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        self.q.save()
        self.fq = get_failed_queue()
        self.w = Worker.create([self.q])


    def test_work_is_unreadable(self):
        """Unreadable jobs are put on the failed queue."""

        self.assertEquals(self.fq.count, 0)
        self.assertEquals(self.q.count, 0)

        # NOTE: We have to fake this enqueueing for this test case.
        # What we're simulating here is a call to a function that is not
        # importable from the worker process.
        job = Job.create(func=div_by_zero, args=(3,))
        job.save()
        job.instance = 'nonexisting_job'
        job.queue = self.q
        job.save()


        self.assertEquals(self.q.count, 1)

        # All set, we're going to process it

        self.w.work(burst=True)   # should silently pass
        self.assertEquals(self.q.count, 0)
        self.assertEquals(self.fq.count, 1)


class TestWorkFails(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        self.fq = get_failed_queue()
        self.w = Worker.create([self.q])
        self.job = self.q.enqueue(div_by_zero)
        self.enqueued_at = self.job.enqueued_at

    def test_work_fails(self):
        """Failing jobs are put on the failed queue."""


        self.w.work(burst=True)  # should silently pass

        # Postconditions
        self.assertEquals(self.q.count, 0)
        self.assertEquals(self.fq.count, 1)

        # Check the job
        job = Job.objects.get(id=self.job.id)
        self.assertEquals(job.origin, self.q.name)

        # Should be the original enqueued_at date, not the date of enqueueing
        # to the failed queue
        self.assertEquals(job.enqueued_at, self.enqueued_at)
        self.assertIsNotNone(job.exc_info)  # should contain exc_info


class TestWorkerCustomExcHandling(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.fq = get_failed_queue()
        def black_hole(job, *exc_info):
            # Don't fall through to default behaviour of moving to failed queue
            return False
        self.black_hole = black_hole
        self.job = self.q.enqueue(div_by_zero)



    def test_custom_exc_handling(self):
        """Custom exception handling."""


        w = Worker.create([self.q], exc_handler=self.black_hole)
        w.work(burst=True)  # should silently pass

        # Postconditions
        self.assertEquals(self.q.count, 0)
        self.assertEquals(self.fq.count, 0)

        # Check the job
        job = Job.objects.get(id=self.job.id)
        self.assertEquals(job.status, Job.FAILED)


class TestWorkerTimeouts(TransactionTestCase):

    def setUp(self):
        self.sentinel_file = '/tmp/.rq_sentinel'
        self.q = Queue()
        self.fq = get_failed_queue()
        self.w = Worker.create([self.q])

    def test_timeouts(self):
        """Worker kills jobs after timeout."""

        # Put it on the queue with a timeout value
        jobr = self.q.enqueue(
                create_file_after_timeout,
                args=(self.sentinel_file, 4),
                timeout=1)

        self.assertEquals(os.path.exists(self.sentinel_file), False)
        self.w.work(burst=True)
        self.assertEquals(os.path.exists(self.sentinel_file), False)

        job = Job.objects.get(id=jobr.id)
        self.assertIn('JobTimeoutException', job.exc_info)

    def tearDown(self):
        try:
            os.unlink(self.sentinel_file)
        except OSError as e:
            if e.errno == 2:
                pass


class TestWorkerSetsResultTTL(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q])

    @params((10,10), (-1,-1), (0, None))
    def test_worker_sets_result_ttl(self, ttl, outcome):
        """Ensure that Worker properly sets result_ttl for individual jobs or deletes them."""
        job = self.q.enqueue(say_hello, args=('Frank',), result_ttl=ttl)
        self.w.work(burst=True)
        try:
            rjob = Job.objects.get(id=job.id)
            result_ttl = rjob.result_ttl
        except Job.DoesNotExist:
            result_ttl = None

        self.assertEqual(result_ttl, outcome)


class TestWorkerDeletesExpiredTTL(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q])
        self.job = self.q.enqueue(say_hello, args=('Bob',), result_ttl=1)
        self.w.work(burst=True)

    def test_worker_deletes_expired_ttl(self):
        """Ensure that Worker deletes expired jobs"""
        time.sleep(1)
        self.w.work(burst=True)
        with self.assertRaises(Job.DoesNotExist) as exc:
            rjob = Job.objects.get(id=self.job.id)


class TestWorkerDequeueTimeout(TransactionTestCase):
    """Simple test to ensure the worker finishes"""

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q],
            expires_after=1,
            default_worker_ttl=1)

    def test_worker_dequeue_timeout(self):
        self.w.work()
        self.assertEqual(self.w._expires_after, -1)


class TestRegisterHeartbeat(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q], name='Test')
        self.w.heartbeat = datetime(2010,1,1, tzinfo=utc)

    def test_worker_register_heartbeat(self):
        self.w.register_heartbeat(timeout=0)
