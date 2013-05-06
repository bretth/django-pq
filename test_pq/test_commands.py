from django.test import TransactionTestCase
from django.core.management import call_command

from pq import Queue, SerialQueue
from pq.worker import Worker


class TestPQWorker(TransactionTestCase):
    reset_sequences = True
    def setUp(self):
        self.q = Queue()

    def test_pq_worker(self):
        call_command('pqworker', 'default', burst=True)


class TestPQWorkerSerial(TransactionTestCase):
    reset_sequences = True
    def setUp(self):
        self.q = Queue()
        self.sq = SerialQueue()

    def test_pq_worker_serial(self):
        call_command('pqworker', 'serial', 'default', burst=True)

