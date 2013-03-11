import sys
import os
import errno
import random
import time
import times
try:
    from procname import setprocname
except ImportError:
    def setprocname(*args, **kwargs):  # noqa
        pass
import socket
import signal
import traceback
import logging


import pkg_resources
from picklefield.fields import PickledObjectField
from django.db import transaction
from django.db import models
from django.conf import settings

from .queue import Queue as PQ
from .queue import get_failed_queue
from .job import Job
from .utils import make_colorizer
from .exceptions import NoQueueError, UnpickleError, DequeueTimeout, StopRequested
from .timeouts import death_penalty_after

VERSION = pkg_resources.require("django-pq")[0].version


green = make_colorizer('darkgreen')
yellow = make_colorizer('darkyellow')
blue = make_colorizer('darkblue')

PQ_DEFAULT_WORKER_TTL = 420 if not hasattr(settings, 'PQ_DEFAULT_WORKER_TTL') else settings.PQ_DEFAULT_WORKER_TTL
PQ_DEFAULT_RESULT_TTL = 500 if not hasattr(settings, 'PQ_DEFAULT_RESULT_TTL') else settings.PQ_DEFAULT_RESULT_TTL

logger = logging.getLogger(__name__)


def iterable(x):
    return hasattr(x, '__iter__')

class Worker(models.Model):

    name = models.CharField(max_length=254, primary_key=True)
    birth = models.DateTimeField(null=True, blank=True)
    expire = models.PositiveIntegerField(null=True, blank=True)
    queue_names = models.CharField(max_length=254, null=True, blank=True)


    @classmethod
    def all(cls, connection='default'):
        """Returns an iterable of all Workers.
        """
        return Worker.objects.using(connection).all()

    @classmethod
    def create(cls, queues, name='worker',
            default_result_ttl=PQ_DEFAULT_RESULT_TTL, connection='default',
            exc_handler=None, default_worker_ttl=PQ_DEFAULT_WORKER_TTL):  # noqa
        """Create a Worker instance without saving to the backend.
        Workers are not persistent but can register themselves.
        """
        w = cls()
        w.connection = connection
        if isinstance(queues, PQ):
            w.queues = [queues]
        else:
            w.queues = queues
        w.name = name
        w.validate_queues()
        w._exc_handlers = []
        w.default_result_ttl = default_result_ttl
        w.default_worker_ttl = default_worker_ttl
        # To save overhead we don't persist state - but we may change this behaviour.
        w.state = 'starting'
        w._is_horse = False
        w._horse_pid = 0
        w._stopped = False
        w.log = logger
        w.failed_queue = get_failed_queue(connection)

        # By default, push the "move-to-failed-queue" exception handler onto
        # the stack
        w.push_exc_handler(w.move_to_failed_queue)
        if exc_handler is not None:
            w.push_exc_handler(exc_handler)
        return w


    def validate_queues(self):  # noqa
        """Sanity check for the given queues."""
        if not iterable(self.queues):
            raise ValueError('Argument queues not iterable.')
        for queue in self.queues:
            if not isinstance(queue, PQ):
                raise NoQueueError('Give each worker at least one Queue.')

    def get_queue_names(self):
        """Returns the queue names of this worker's queues."""
        return map(lambda q: q.name, self.queues)


    def set_queues(self, addqueues):
        self._queues = addqueues
        self.queue_names = self.get_queue_names()

    def get_queues(self):
        return self._queues
    queues = property(get_queues, set_queues)

    @property  # noqa
    def calculated_name(self):
        """Returns the name of the worker, under which it is registered to the
        monitoring system.

        By default, the name of the worker is constructed from the current
        (short) host name and the current PID.
        """
        #if self._name is None:
        hostname = socket.gethostname()
        shortname, _, _ = hostname.partition('.')
        name = '%s.%s' % (shortname, self.pid)
        return name


    @property
    def pid(self):
        """The current process ID."""
        return os.getpid()

    @property
    def horse_pid(self):
        """The horse's process ID.  Only available in the worker.  Will return
        0 in the horse part of the fork.
        """
        return self._horse_pid

    @property
    def is_horse(self):
        """Returns whether or not this is the worker or the work horse."""
        return self._is_horse

    def procline(self, message):
        """Changes the current procname for the process.

        This can be used to make `ps -ef` output more readable.
        """
        setprocname('pq: %s' % (message,))


    def register_birth(self):  # noqa
        """Registers its own birth, savingg to Postgres"""
        self.log.debug('Registering birth of worker %s' % (self.calculated_name,))
        with transaction.commit_on_success(using=self.connection):
            if Worker.objects.using(self.connection).filter(name=self.calculated_name)[:]:
                raise ValueError(
                        'There exists an active worker named \'%s\' '
                        'already.' % (self.calculated_name,))
            self.name = self.calculated_name
            self.birth = times.now()
            self.queue_names = ','.join(self.get_queue_names())
            self.expire = self.default_worker_ttl
            self.save()

    def register_death(self):
        """Registers its own death deleting the instance"""
        self.log.debug('Registering death')
        self.delete()

    @property
    def stopped(self):
        return self._stopped

    def _install_signal_handlers(self):
        """Installs signal handlers for handling SIGINT and SIGTERM
        gracefully.
        """

        def request_force_stop(signum, frame):
            """Terminates the application (cold shutdown).
            """
            self.log.warning('Cold shut down.')

            # Take down the horse with the worker
            if self.horse_pid:
                msg = 'Taking down horse %d with me.' % self.horse_pid
                self.log.debug(msg)
                try:
                    os.kill(self.horse_pid, signal.SIGKILL)
                except OSError as e:
                    # ESRCH ("No such process") is fine with us
                    if e.errno != errno.ESRCH:
                        self.log.debug('Horse already down.')
                        raise
            raise SystemExit()

        def request_stop(signum, frame):
            """Stops the current worker loop but waits for child processes to
            end gracefully (warm shutdown).
            """
            self.log.debug('Got signal %s.' % signal_name(signum))

            signal.signal(signal.SIGINT, request_force_stop)
            signal.signal(signal.SIGTERM, request_force_stop)

            msg = 'Warm shut down requested.'
            self.log.warning(msg)

            # If shutdown is requested in the middle of a job, wait until
            # finish before shutting down
            if self.state == 'busy':
                self._stopped = True
                self.log.debug('Stopping after current horse is finished. '
                               'Press Ctrl+C again for a cold shutdown.')
            else:
                raise StopRequested()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)


    def work(self, burst=False):  # noqa
        """Starts the work loop.

        Pops and performs all jobs on the current list of queues.  When all
        queues are empty, block and wait for new jobs to arrive on any of the
        queues, unless `burst` mode is enabled.

        The return value indicates whether any jobs were processed.
        """
        self._install_signal_handlers()

        did_perform_work = False
        self.register_birth()
        self.log.info('RQ worker started, version %s' % VERSION)
        self.state = 'starting'
        try:
            while True:
                if self.stopped:
                    self.log.info('Stopping on request.')
                    break
                self.state = 'idle'
                qnames = self.get_queue_names()
                self.procline('Listening on %s' % ','.join(qnames))
                self.log.info('')
                self.log.info('*** Listening on %s...' % \
                        green(', '.join(qnames)))
                timeout = None if burst else max(1, self.default_worker_ttl - 60)
                try:
                    result = PQ.dequeue_any(self.queues, timeout)
                    if result is None:
                        break
                except StopRequested:
                    break

                self.state = 'busy'

                job, queue = result
                # Use the public setter here, to immediately update Redis
                job.status = Job.STARTED
                job.save()
                self.log.info('%s: %s (%s)' % (green(queue.name),
                    blue(job.description), job.id))

                #self.connection.expire(self.key, (job.timeout or 180) + 60)
                self.fork_and_perform_job(job)
                #self.connection.expire(self.key, self.default_worker_ttl)

                did_perform_work = True
        finally:
            if not self.is_horse:
                self.register_death()
        return did_perform_work

    def fork_and_perform_job(self, job):
        """Spawns a work horse to perform the actual work and passes it a job.
        The worker will wait for the work horse and make sure it executes
        within the given timeout bounds, or will end the work horse with
        SIGALRM.
        """
        child_pid = os.fork()
        if child_pid == 0:
            self.main_work_horse(job)
        else:
            self._horse_pid = child_pid
            self.procline('Forked %d at %d' % (child_pid, time.time()))
            while True:
                try:
                    os.waitpid(child_pid, 0)
                    break
                except OSError as e:
                    # In case we encountered an OSError due to EINTR (which is
                    # caused by a SIGINT or SIGTERM signal during
                    # os.waitpid()), we simply ignore it and enter the next
                    # iteration of the loop, waiting for the child to end.  In
                    # any other case, this is some other unexpected OS error,
                    # which we don't want to catch, so we re-raise those ones.
                    if e.errno != errno.EINTR:
                        raise

    def main_work_horse(self, job):
        """This is the entry point of the newly spawned work horse."""
        # After fork()'ing, always assure we are generating random sequences
        # that are different from the worker.
        random.seed()

        # Always ignore Ctrl+C in the work horse, as it might abort the
        # currently running job.
        # The main worker catches the Ctrl+C and requests graceful shutdown
        # after the current work is done.  When cold shutdown is requested, it
        # kills the current job anyway.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        self._is_horse = True
        self.log = logger

        success = self.perform_job(job)

        # os._exit() is the way to exit from childs after a fork(), in
        # constrast to the regular sys.exit()
        os._exit(int(not success))

    def perform_job(self, job):
        """Performs the actual work of a job.  Will/should only be called
        inside the work horse's process.
        """
        self.procline('Processing %s from %s since %s' % (
            job.func_name,
            job.origin, time.time()))

        try:
            with death_penalty_after(job.timeout or 180):
                rv = job.perform()

            # Pickle the result in the same try-except block since we need to
            # use the same exc handling when pickling fails
            job.result = rv
            job.status = Job.FINISHED
            job.ended_at = times.now()
            job.result_ttl = job.get_ttl(self.default_result_ttl)
            if job.result_ttl > 0:
                job.save()
            else:
                job.delete()

        except:
            job.status = Job.FAILED
            job.save()
            self.handle_exception(job, *sys.exc_info())
            return False

        if rv is None:
            self.log.info('Job OK')
        else:
            self.log.info('Job OK, result = %s' % (yellow(unicode(rv)),))

        if job.result_ttl == 0:
            self.log.info('Result discarded immediately.')
        elif job.result_ttl > 0:
            self.log.info('Result is kept for %d seconds.' % job.result_ttl)
        else:
            self.log.warning('Result will never expire, clean up result key manually.')

        return True


    def handle_exception(self, job, *exc_info):
        """Walks the exception handler stack to delegate exception handling."""
        exc_string = ''.join(
                traceback.format_exception_only(*exc_info[:2]) +
                traceback.format_exception(*exc_info))
        self.log.error(exc_string)

        for handler in reversed(self._exc_handlers):
            self.log.debug('Invoking exception handler %s' % (handler,))
            fallthrough = handler(job, *exc_info)

            # Only handlers with explicit return values should disable further
            # exc handling, so interpret a None return value as True.
            if fallthrough is None:
                fallthrough = True

            if not fallthrough:
                break

    def move_to_failed_queue(self, job, *exc_info):
        """Default exception handler: move the job to the failed queue."""
        exc_string = ''.join(traceback.format_exception(*exc_info))
        self.log.warning('Moving job to %s queue.' % self.failed_queue.name)
        self.failed_queue.quarantine(job, exc_info=exc_string)

    def push_exc_handler(self, handler_func):
        """Pushes an exception handler onto the exc handler stack."""
        self._exc_handlers.append(handler_func)

    def pop_exc_handler(self):
        """Pops the latest exception handler off of the exc handler stack."""
        return self._exc_handlers.pop()