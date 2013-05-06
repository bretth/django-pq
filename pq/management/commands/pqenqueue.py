from django.core.management.base import BaseCommand
from optparse import make_option

from django.conf import settings

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Enqueue a function with or without arguments"
    args = "<function arg arg ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="A timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="A timeout in seconds"),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue

        func = args[0]
        args = args[1:]
        timeout = options.get('timeout')
        queue = options.get('queue')
        if options['serial']:
            queue = queue or 'serial'
            q = SerialQueue.create(queue)
        else:
            queue = queue or 'default'
            q = Queue.create(queue)
        if timeout:
            q.enqueue(func, *args, timeout=timeout)
        else:
            q.enqueue(func, *args)
