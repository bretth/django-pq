from django.test import TransactionTestCase
from django.core.management import call_command

from pq.worker import Worker


class TestPQWorker(TransactionTestCase):
    reset_sequences = True
    def test_pq_worker(self):
        call_command('pqworker', 'default', 'q2', burst=True)

