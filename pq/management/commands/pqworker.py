import logging
import time
import sys
from django.core.management.base import BaseCommand
from optparse import make_option

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Starts a pq worker on all available queues or just specified queues in order"
    args = "[queue queue ...]"


    option_list = BaseCommand.option_list + (
        make_option('--burst', '-b', action='store_true', dest='burst',
            default=False, help='Run in burst mode (quit after all work is done)'),
        make_option('--name', '-n', default=None, dest='name',
            help='Specify a different name'),
        make_option('--connection', '-c', action='store', default='default',
                    help='Report exceptions to this Sentry DSN'),
        make_option('--sentry-dsn', action='store', default=None, metavar='URL',
                    help='Report exceptions to this Sentry DSN'),
        make_option('--terminate', action='store_true', dest='terminate',
                    help='Terminate worker'),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.

        """
        from django.conf import settings
        from pq.queue import Queue, SerialQueue
        from pq.worker import Worker

        sentry_dsn = options.get('sentry_dsn')
        if not sentry_dsn:
            sentry_dsn = settings.SENTRY_DSN if hasattr(settings, 'SENTRY_DSN') else None

        verbosity = int(options.get('verbosity'))
        queues = []
        if options.get('terminate'):
            workern = [w.name for w in Worker.objects.all()]

            for worker in Worker.objects.all()[:]:
                worker.stop = True
                worker.save()

            print('Terminating %s ...' % ' '.join(workern))  
            while Worker.objects.all():
                time.sleep(5)
            
            return
        if not args:
            args = [q[0] for q in Queue.objects.values_list('name').exclude(name='failed')]
            args.sort()
        if not args:
            print('There are no queues to work on')
            sys.exit(1)
        for queue in args:
            try:
                q = Queue.objects.get(name=queue)
            except Queue.DoesNotExist:
                print("The '%s' queue does not exist. Use the pqcreate command to create it." % queue)
                continue
            if q.serial:
                q = SerialQueue.objects.get(name=queue)
            else:
                q = Queue.objects.get(name=queue)
            q.connection = options['connection']
            q._saved = True
            queues.append(q)
        if queues:
            w = Worker.create(queues, name=options.get('name'), connection=options['connection'])

            # Should we configure Sentry?
            if sentry_dsn:
                from raven import Client
                from pq.contrib.sentry import register_sentry
                client = Client(sentry_dsn)
                register_sentry(client, w)

            w.work(burst=options['burst'])

