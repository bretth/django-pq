import time
from datetime import timedelta, datetime
from django.test import TestCase, TransactionTestCase
from django.utils.timezone import utc, now
from dateutil.relativedelta import relativedelta
from nose2.tools import params

from pq.job import Job
from pq import Queue
from .fixtures import some_calculation, say_hello, Calculator, do_nothing

class TestJobCreation(TestCase):

    def test_job_create(self):
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.description)
        self.assertIsNone(job.instance)

        # Job data is set...
        self.assertEquals(job.func, some_calculation)
        self.assertEquals(job.args, (3, 4))
        self.assertEquals(job.kwargs, {'z': 2})

        # ...but metadata is not
        self.assertIsNone(job.origin)
        self.assertIsNone(job.enqueued_at)

    def test_create_instance_method_job(self):
        """Creation of jobs for instance methods."""
        c = Calculator(2)
        job = Job.create(func=c.calculate, args=(3, 4))

        # Job data is set
        self.assertEquals(job.func, c.calculate)
        self.assertEquals(job.instance, c)
        self.assertEquals(job.args, (3, 4))

    def test_create_job_from_string_function(self):
        """Creation of jobs using string specifier."""
        job = Job.create(func='test_pq.fixtures.say_hello', args=('World',))

        # Job data is set
        self.assertEquals(job.func, say_hello)
        self.assertIsNone(job.instance)
        self.assertEquals(job.args, ('World',))


class TestScheduledJobCreation(TestCase):

    def test_scheduled_job_create(self):
        """ Test extra kwargs """
        dt = datetime(2013,1,1, tzinfo=utc)
        rd = relativedelta(months=1, days=-1)
        job = Job.create(func=some_calculation,
            args=(3, 4), kwargs=dict(z=2),
            scheduled_for = dt,
            repeat = -1,
            interval = rd,
            between = '0-24'
            )
        job.save()
        job = Job.objects.get(pk=job.id)
        self.assertEqual(rd, job.interval)
        self.assertEqual(dt, job.scheduled_for)



class TestJobSave(TransactionTestCase):

    def setUp(self):
        self.job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

    def test_job_save(self):  # noqa
        """Storing jobs."""
        self.job.save()
        self.assertIsNotNone(self.job.id)


class Test_get_job_or_promise(TransactionTestCase):
    """Test the Job._get_job_or_promise classmethod"""

    def setUp(self):
        self.q = Queue(scheduled=True)
        # simulate the default worker timeout
        self.timeout = 60
        future = now() + timedelta(seconds=self.timeout/2)
        # enqueue a job for 30 seconds time in the future
        self.job = self.q.schedule_call(future, do_nothing)


    def test_get_job_or_promise(self):
        """Test get a promise of a job in the future"""

        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, self.timeout)
        self.assertLessEqual(timeout, self.timeout)
        self.assertIsNone(job)
        self.assertEqual(promise, self.q.name)

    def test_get_no_job_no_promise(self):
        """Test get no job and no promise"""

        # job is in the future beyond the current
        # worker timeout
        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, 1)
        self.assertEqual(timeout, 1)
        self.assertIsNone(job)
        self.assertIsNone(promise)

    def test_get_earlier_job_no_promise(self):
        """Test get earlier job and no promise"""
        # Job enqueue after the first scheduled job
        # but to be exec ahead of the scheduled job
        now_job = self.q.enqueue(do_nothing)
        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, 60)
        # timeout should remain the same
        self.assertEqual(timeout, 60)
        self.assertEqual(now_job.id, job.id)
        self.assertIsNone(promise)


class Test_get_job_no_promise(TransactionTestCase):

    def setUp(self):
        # setup a job in the very near future which
        # should execute
        self.q = Queue(scheduled=True)
        # simulate the default worker timeout
        self.timeout = 60
        future = now() + timedelta(seconds=1)
        # enqueue a job for 1 second time in the future
        self.job = self.q.schedule_call(future, do_nothing)
        time.sleep(1)

    def test_get_job_no_promise(self):
        """Test get job and no promise"""

        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, self.timeout)
        self.assertEqual(timeout, self.timeout)
        self.assertEquals(job.id, self.job.id)
        self.assertIsNone(promise)


class TestJobSchedule(TestCase):

    def test_job_get_schedule_options(self):
        """Test the job schedule property"""
        j = Job.create(
            do_nothing,
            interval=600,
            between='2-4',
            repeat=10,
            weekdays=(0,1,2)
            )
        self.assertIsNotNone(j.get_schedule_options())

