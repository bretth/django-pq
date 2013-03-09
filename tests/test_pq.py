from django.test import TestCase, TransactionTestCase

from pq import Queue

class TestQueueCreation(TransactionTestCase):

    def test_default_queue_create(self):
        queue = Queue()
        self.assertEqual(queue.name, 'default')
