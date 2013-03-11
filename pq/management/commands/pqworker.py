import logging
from django.core.management.base import BaseCommand
from optparse import make_option


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Starts a pq worker"
    args = "<queue queue ...>"


    option_list = BaseCommand.option_list + (
        make_option('--burst', '-b', action='store_true', dest='burst',
            default=False, help='Run in burst mode (quit after all work is done)'),
        make_option('--name', '-n', default=None, dest='name',
            help='Specify a different name'),
        make_option('--sentry-dsn', action='store', default=None, metavar='URL',
                    help='Report exceptions to this Sentry DSN'),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.

        """
        from django.conf import settings
        from pq.queue import Queue
        from pq.worker import Worker

        sentry_dsn = options.get('sentry_dsn')
        if not sentry_dsn:
            sentry_dsn = settings.SENTRY_DSN if hasattr(settings, 'SENTRY_DSN') else None

        verbosity = int(options.get('verbosity'))

        queues = map(Queue.create, args)
        w = Worker.create(queues, name=options.get('name'))

        # Should we configure Sentry?
        if sentry_dsn:
            from raven import Client
            from pq.contrib.sentry import register_sentry
            client = Client(args.sentry_dsn)
            register_sentry(client, w)

        w.work(burst=options['burst'])

