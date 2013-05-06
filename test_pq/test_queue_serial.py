
import time
from datetime import datetime, timedelta
from django.utils.timezone import utc, now
from django.test import TestCase, TransactionTestCase

from pq import Worker
from pq.queue import SerialQueue, Queue
from pq.exceptions import DequeueTimeout

from .fixtures import do_nothing



class TestSerialQueueCreate(TestCase):

    def test_serial_queue_create(self):
        sq = SerialQueue.create()
        self.assertTrue(sq.serial)


class TestQueueCreationTwoQueueTypes(TestCase):

    def test_default_queue_create_multiple(self):
        queue = Queue.create()
        self.assertEqual(queue.name, 'default')
        queue = SerialQueue.create()
        self.assertEqual(queue.name, 'serial')


class TestSerialQueueMethods(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.sq.save()

    def test_acquire_lock(self):
        """Acquire a lock for an arbitrary time"""
        self.assertTrue(self.sq.acquire_lock(60))


class TestSerialQueueLock(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.sq.save()
        self.sq.acquire_lock(1)

    def test_acquire_already_locked(self):
        self.assertFalse(self.sq.acquire_lock())

    def test_lock_expires(self):
        time.sleep(1)
        self.assertTrue(self.sq.acquire_lock())



class TestDequeueAnySerialJobs(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.job = self.sq.enqueue(do_nothing)

    def test_dequeue_any_serial(self):
        job, queue = Queue.dequeue_any([self.sq], timeout=10)
        self.assertEquals(job.func, do_nothing)


class TestDequeueAnyLockedSerialJobs(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.job = self.sq.enqueue(do_nothing)
        self.sq.acquire_lock(10)

    def test_dequeue_any_serial_lock(self):
        """Test that it raises a DequeueTimeout timeout"""
        with self.assertRaises(DequeueTimeout):
            Queue.dequeue_any([self.sq], timeout=1)


class TestDequeueLockExpiresSerialJobs(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.job = self.sq.enqueue(do_nothing)
        self.sq.acquire_lock(1)

    def test_dequeue_any_serial_lock_expired(self):
        """Test that it raises a DequeueTimeout timeout"""
        time.sleep(1)
        job, queue = Queue.dequeue_any([self.sq], timeout=1)
        self.assertEquals(self.job.id, job.id)


class TestQueueCreationConflictIssue2(TransactionTestCase):
    "https://github.com/bretth/django-pq/issues/2"

    def setUp(self):
        self.q = SerialQueue.create()
        self.assertTrue(self.q.serial)

    def test_queue_creation_conflict_issue2(self):
        """Ordinary queue shouldn't ever become a serial queue"""
        q = Queue.create()
        self.assertFalse(q.serial)
        q.enqueue(do_nothing)
        self.q.enqueue(do_nothing)
        w = Worker([q, self.q])
        w.work(burst=True)

