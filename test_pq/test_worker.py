from django.test import TransactionTestCase

from pq import Queue
from pq.worker import Worker

from .fixtures import say_hello

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
