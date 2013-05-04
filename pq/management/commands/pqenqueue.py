from django.core.management.base import BaseCommand
from optparse import make_option

from django.conf import settings

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Enqueue a function with or without arguments"
    args = "<function arg arg ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue',
            default='default', help='Specify the queue [default]'),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="A timeout in seconds"),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq import Queue

        func = args[0]
        args = args[1:]
        timeout = options.get('timeout')
        q = Queue(options['queue'])
        if timeout:
            q.enqueue(func, *args, timeout=timout)
        else:
            q.enqueue(func, *args)
