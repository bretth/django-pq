from django.core.management.base import BaseCommand
from optparse import make_option

from django.conf import settings

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Enqueue a function"
    args = "<function arg arg ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--conn', '-c', dest='conn', default='default',
            help='Specify a connection [default]'),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="A timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="A timeout in seconds"),
        make_option('--sync', action="store_true", default=False, dest='sync',
            help="Perform the task now")
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue
        verbosity = int(options.get('verbosity', 1))
        func = args[0]
        args = args[1:]
        async = not options.get('sync')
        timeout = options.get('timeout')
        queue = options.get('queue')
        conn = options.get('conn')
        if options['serial']:
            queue = queue or 'serial'
            q = SerialQueue.create(queue, connection=conn)
        else:
            queue = queue or 'default'
            q = Queue.create(queue, connection=conn)
        if timeout:
            job = q.enqueue_call(func, args=args, timeout=timeout, async=async)
        else:
            job = q.enqueue_call(func, args=args, async=async)
        if verbosity and job.id:
            print('Job %i created' % job.id)
        elif verbosity:
            print('Job complete')