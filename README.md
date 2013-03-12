django-pq
==========

A task queue based on the elegant [RQ](http://python-rq.org) but with a django postgresql backend.

RQ sets a low barrier for entry, and django-pq takes it lower for sites that can’t or don’t want to use Redis in their stack, and are happy to trade off performance for the transactional integrity of Postgres. As additional throughput is required you should be able to switch out or mix django-pq with the more performant Redis based RQ with only trival code changes.

Django-pq is currently considered alpha quality, and is probably not suitable for production.

Installation
--------------

Currently only available through github:

    $ pip install https://github.com/bretth/django-pq/zipball/master

Getting started
----------------

If you have used RQ then you’ll know django-pq but lets start with the RQ example.

    import requests

    def count_words_at_url(url):
        resp = requests.get(url)
        return len(resp.text.split())

Create the queue.

    from pq import Queue
    q = Queue()

Enqueue the function.

    q.enqueue(count_words_at_url, 'http://python-rq.org')


Consume your queue with a worker.

    $ pqworker —burst
     *** Listening for work on default
     Got count_words_at_url('http://python-rq.org') from default
      Job result = 818
     *** Listening for work on default


Queues
---------

Since django-pq is uses django models we have one piece of syntactic sugar to maintain compatibility with RQ.

    from pq import Queue
    # create a default queue called ‘default’
    queue = Queue()

Is syntactic sugar for:

    from  pq.queue import Queue
    queue = Queue.create()

Some more queue creation examples:

    # name it
    q = Queue('farqueue')

    # run synchronously when settings.DEBUG == True
    from django.conf import settings

    q = Queue(async=settings.DEBUG)  # Useful to set this to True for tests

    # Up the timeout for slow jobs to 10 minutes
    q = Queue(timeout=600)

    # Connect to a different settings.DATABASES alias named `happy-db`
    q = Queue(connection='happy-db')

 Define or import a function or class method to enqueue:

    def say_hello(name=None):
        """A job with a single argument and a return value."""
        if name is None:
                         name = 'Stranger'
        return 'Hi there, %s!' % (name,)

    class Calculator(object):
        """Test instance methods."""
        def __init__(self, denominator):
                        self.denominator = denominator

        def calculate(self, x, y):
                return x * y / self.denominator

 Enqueue your jobs in any of the following ways:

    q.enqueue(say_hello, kwargs=‘You’)

    # then with a shorter timeout than 10 minutes
    q.enqueue(say_hello, timeout=60)

    #Instance methods:
    calc = Calculator(2)
    q.enqueue(calc.calculate, args=(4,5))

    # with the @job decorator
    from pq.decorators import job

    # decorate the function to be processed by the ‘default’ queue
    @job(‘default’)
    def say_hello(name=None):
        """A job with a single argument and a return value."""
        if name is None:
                         name = 'Stranger'
        return 'Hi there, %s!' % (name,)

    # add a job to the queue
    job = add.delay(kwargs=‘friend’)

Results
---------

By default, jobs should execute within 180 seconds. You can alter the default time in your django PQ_DEFAULT_JOB_TIMEOUT setting. After that, the worker kills the work horse and puts the job onto the failed queue, indicating the job timed out.

If a job requires more (or less) time to complete, the default timeout period can be loosened (or tightened), by specifying it as a keyword argument to the Queue.enqueue() call, like so:

    q = Queue
    q.enqueue(func=mytask, args=(foo,), kwargs={'bar': qux}, timeout=600)


Completed jobs hang around for a minimum TTL (time to live) of 500 seconds. Since Postgres doesn’t have an expiry option like Redis the worker will periodically poll the database for jobs to delete hence the minimum TTL. The TTL can be altered per job or through a django setting PQ_DEFAULT_RESULT_TTL.

    q.enqueue(func=mytask, result_ttl=0)  # out of my sight immediately
    q.enqueue(func=mytask, result_ttl=86400)  # love you long time
    q.enqueue(func=mytask, result_ttl=-1)  # together forever baby!

Workers
--------

Work is done through pqworker, a django management command. To accept work on the fictional `high` `default` `low` queues:

    $ ./manage.py pqworker high default low
    *** Listening for work on high, default, low
    Got send_newsletter('me@example.com') from default
    Job ended normally without result
    *** Listening for work on high, default, low

If you don’t see any output you might need to configure your django project LOGGING. Here’s an example configuration that will print to the console

    LOGGING = {
    	'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'standard': {
                'format': '[%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'console':{
                'level':'DEBUG',
                'class':"logging.StreamHandler",
                'formatter': 'standard'
            },
        },
        'loggers': {
            'pq.management.commands.pqworker': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True
            },
        }
    }



Queue priority is in the order they are listed, so if the worker never finishes processing the high priority queue the other queues will never be consumed.

To exit after all work is consumed:

    $ ./manage.py pqworker default —burst

More examples:


    $ ./manage.py pqworker default —name=doug  # change the name from the default hostname
    $ ./manage.py pqworker default --connection=[your-db-alias]  # use a different database alias instead of default
    $ ./manage.py pqworker default —-sentry-dsn=SENTRY_DSN  # can also do this in settings at SENTRY_DSN


To implement a worker in code:

    from pq.worker import Worker

    # note there is no syntactic sugar for Workers
    w = Worker.create()


Monitoring [Not Yet Implemented]
---------------------------------

Jobs, Queues and Workers are monitored through the django admin or the pqinfo command. To cut down some of the overhead of managing workers, they are registered and destroyed on the database but unlike RQ do not store their current state (idle, busy etc).

Connections
------------

Django-pq uses the django backend in place of the RQ Redis connections, so you pass in a connection by referring to it's alias in your django DATABASES settings. Surprise surprise we use 'default' if no connection is defined.

    q = Queue(connection='default')
    w = Worker.create(connection='default')

It was originally intended to use Postgresql specific features in the backend such as asynchronous notifications but that proved more effort than it was worth so other backends that support transactions should work fine. If your backend doesn't support transactions then you should limit the number of workers to 1 to avoid errors.

Exceptions
-----------

Jobs that raise exceptions go to the `failed` queue. You can register a custom handler as per RQ:

    w = Worker.create([q], exc_handler=my_handler)

    def my_handler(job, exc_type, exc_value, traceback):
        # do custom things here
        # for example, write the exception info to a DB
        ...
    # You might also see the three exception arguments encoded as:

    def my_handler(job, *exc_info):
        # do custom things here

Settings
---------

All settings are optional. Defaults listed below.

    SENTRY_DSN  # as per sentry
    PQ_DEFAULT_RESULT_TTL = 500  # minumum ttl for jobs
    PQ_DEFAULT_WORKER_TTL = 420  # worker will refresh the connection
    PQ_DEFAULT_JOB_TIMEOUT = 180  # jobs that exceed this time are failed
    PQ_POLL_CYCLE = 60  # the worker will poll for work every 60 seconds


Development
------------

Contributions welcome.

Unit testing with nose2 and my nose2django plugin. To run the tests:

    $ pip install -r requirements
    $ nose2

I have been judicious about which tests were ported across from RQ, but hooray for tests. To make it easier to panel-beat smashed code django-pq does use setUp as its creator intended.

I intend to stick as closely to the documented RQ api as possible with minimal divergence.

Acknowledgements
-----------------

Without RQ (and by extension Vincent Driessen), django-pq would not exist since 90%+ of the codebase comes from that project. RQ is licensed according the BSD license [here](https://raw.github.com/nvie/rq/master/LICENSE).
