from django.test import TestCase, TransactionTestCase

from pq.job import Job
from .fixtures import some_calculation, say_hello, Calculator

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


class TestJobSave(TransactionTestCase):

    def setUp(self):
        self.job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

    def test_job_save(self):  # noqa
        """Storing jobs."""
        self.job.save()
        self.assertIsNotNone(self.job.id)

