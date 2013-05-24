from django.core.management.base import BaseCommand
from optparse import make_option

from django.conf import settings

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Create a queue"
    args = "<queue queue ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--conn', '-c', dest='conn', default='default',
            help='Specify a connection [default]'),
        make_option('--scheduled', action="store_true", default=False, 
            dest="scheduled", help="Schedule jobs in the future"),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="Default timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="A timeout in seconds"),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue
        verbosity = int(options.get('verbosity', 1))
        timeout = options.get('timeout')
        for queue in args:
            if options['serial']:
                q = SerialQueue.create(queue)
            else:
                q = Queue.create(queue)
            q.connection = options.get('conn')
            q.scheduled = options.get('scheduled')
            if timeout:
                q.default_timeout = timeout
            q.save()

