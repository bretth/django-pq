from django.core.management.base import BaseCommand
from optparse import make_option

from six import integer_types
from dateutil import parser
from django.conf import settings
from django.utils.timezone import now, get_default_timezone

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Schedule a function 'now' or at a future date."
    args = "<function now|ISO8601 arg arg ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--conn', '-c', dest='conn', default='default',
            help='Specify a connection [default]'),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="A timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="Serial queue"),
        make_option('--repeat', '-r', type="int", dest='repeat', default=0,
            help="Repeat number of times or -1 for indefinitely"),
        make_option('--interval', '-i', type="int", dest='interval', default=0,
            help="Interval seconds between repeats"),
        make_option('--between', '-b', dest='between', default='',
            help="Restricted time"),
        make_option('--mo', action="store_const", const=0, dest='mo', 
            help="Monday"),
        make_option('--tu', action="store_const", const=1, dest='tu', 
            help="Tuesday"),
        make_option('--we', action="store_const", const=2, dest='we', 
            help="Wednesday"),
        make_option('--th', action="store_const", const=3, dest='th', 
            help="Thursday"),
        make_option('--fr', action="store_const", const=4, dest='fr', 
            help="Friday"),
        make_option('--sa', action="store_const", const=5, dest='sa', 
            help="Saturday"),
        make_option('--su', action="store_const", const=6, dest='su', 
            help="Sunday"),
        make_option('--mtwtf', action="store_true", dest='mtwtf', 
            help="Monday to Friday"),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue
        verbosity = int(options.get('verbosity', 1))
        func = args[1]
        if args[0].lower() == 'now':
            at = now()
        else:
            at = parser.parse(args[0])
        if not at.tzinfo:
            at = at.replace(tzinfo=get_default_timezone())

        args = args[2:]
        if options.get('mtwtf'):
            weekdays = (0,1,2,3,4)
        else:
            weekdays = (
                options.get('mo'),
                options.get('tu'),
                options.get('we'),
                options.get('th'),
                options.get('fr'),
                options.get('sa'),
                options.get('su'),
                )

            weekdays = [w for w in weekdays if isinstance(w, integer_types)]
        timeout = options.get('timeout')
        queue = options.get('queue')
        conn = options.get('conn')
        if options['serial']:
            queue = queue or 'serial'
            q = SerialQueue.create(queue, connection=conn, scheduled=True)
        else:
            queue = queue or 'default'
            q = Queue.create(queue, connection=conn, scheduled=True)
        job = q.schedule_call(at, func, args=args, 
            timeout=timeout,
            repeat=options['repeat'],
            interval=options['interval'],
            between=options['between'],
            weekdays=weekdays
            )
        if verbosity:
            print('Job %i created' % job.id)

