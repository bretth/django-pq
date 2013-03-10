from django.test import TestCase, TransactionTestCase

from pq import Queue
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
