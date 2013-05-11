from datetime import datetime
from django.test import TestCase, TransactionTestCase
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.contrib.auth.models import User
from nose2.tools import params

from pq.job import (Job, FailedJob, DequeuedJob,
                     QueuedJob, ScheduledJob)
from pq.worker import Worker
from pq import Queue
from pq.queue import FailedQueue
from pq.admin import requeue_failed_jobs

from .fixtures import say_hello, div_by_zero

class TestJobAdmin(TransactionTestCase):
    def setUp(self):
        password = 'test'
        user = User.objects.create_superuser('test', 'test@test.com', password)
        self.client.login(username = user.username, password = password)
        self.q = Queue()
        self.q.enqueue_call(say_hello, args=('you',))
        self.q.enqueue_call(div_by_zero, args=(1,))
        self.q.schedule(datetime(2099,1,1), say_hello, 'later')
        w = Worker.create(self.q)
        w.work(burst=True)
        self.q.enqueue_call(say_hello, args=('me',))
        

    @params(
        ("failedjob", FailedJob),
        ("queuedjob", QueuedJob),
        ("dequeuedjob", DequeuedJob),
        ("scheduledjob", ScheduledJob))
    def test_changelist(self, modelname, Model):
        url = reverse("admin:pq_%s_changelist" % modelname)
        response = self.client.get(url, follow = True)
        self.failUnlessEqual(response.status_code, 200,
                     "%s != %s -> %s, url: %s" % (response.status_code, 200, repr(Model), url))

class TestRequeueAdminAction(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        self.q.enqueue_call(div_by_zero, args=(1,))
        w = Worker.create(self.q)
        w.work(burst=True)

    def test_requeue_admin_action(self):
        self.assertEqual(0, len(Job.objects.filter(queue_id='default')))
        requeue_failed_jobs(None, None, Job.objects.filter(queue_id='failed'))
        self.assertEqual(0, len(Job.objects.filter(queue_id='failed')))

        self.assertEqual('test_pq.fixtures.div_by_zero', Job.objects.get(queue_id='default').func_name)
