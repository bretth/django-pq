from dateutil.relativedelta import relativedelta
from django.test import TransactionTestCase
from django.core.management import call_command

from pq import Queue, SerialQueue
from pq.worker import Worker
from pq.queue import Queue as PQ
from pq.job import Job


class TestPQWorker(TransactionTestCase):
    reset_sequences = True
    def setUp(self):
        self.q = Queue()
        self.q.save_queue()

    def test_pq_worker(self):
        call_command('pqworker', 'default', burst=True)

    def test_pq_worker_all_queues(self):
        call_command('pqworker', burst=True)


class TestPQWorkerSerial(TransactionTestCase):
    reset_sequences = True
    def setUp(self):
        self.q = Queue()
        self.q.save_queue()
        self.sq = SerialQueue()
        self.sq.save_queue()

    def test_pq_worker_serial(self):
        call_command('pqworker', 'serial', 'default', burst=True)


class TestPQSchedule(TransactionTestCase):
    reset_sequences = True

    def test_pqschedule(self):
        call_command('pqschedule', '2099-01-01', 'test_pq.fixtures.do_nothing', 
            mo=0, tu=1, we=2, th=3, fr=4, sa=5, su=6,
            serial=True, queue='blah', repeat=-1, interval=60, 
            between='2-4', timeout=300)

        j = Job.objects.all()[0]
        self.assertEqual(j.origin, 'blah')
        q = PQ.objects.get(name=j.origin)
        self.assertTrue(q.serial)
        self.assertTrue(q.scheduled)
        self.assertEqual(j.weekdays, [0,1,2,3,4,5,6])
        self.assertEqual(j.repeat, -1)
        self.assertEqual(j.interval, relativedelta(minutes=1))
        self.assertEqual(j.between, '2-4')
        self.assertEqual(j.timeout, 300)


class TestPQEnqueue(TransactionTestCase):
    reset_sequences = True

    def test_pqenqueue_sync(self):
        call_command('pqenqueue', 'test_pq.fixtures.do_nothing', 
            serial=True, queue='blah', timeout=300, sync=True)
        self.assertFalse(Job.objects.all())

    def test_pqenqueue(self):
        call_command('pqenqueue', 'test_pq.fixtures.do_nothing', 
            serial=True, queue='blah', timeout=300)
        j = Job.objects.all()[0]
        self.assertEqual(j.origin, 'blah')
        q = PQ.objects.get(name=j.origin)
        self.assertTrue(q.serial)
        self.assertFalse(q.scheduled)
        self.assertEqual(j.timeout, 300)
        self.assertEqual(j.status, Job.QUEUED)





