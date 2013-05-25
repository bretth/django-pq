django-pq
==========

A task queue with scheduling and simple workflow engine based on the elegant RQ_ but with a django postgresql backend, using postgresql's asynchronous notifications to wait for work.

RQ sets a low barrier for entry, and django-pq takes it lower for sites that can’t or don’t want to use Redis in their stack. By using django-pq you are trading off throughput on cheap tasks for the transactional integrity of Postgresql. For tasks that are expected to complete in a few milliseconds or less such as internal messaging you can expect RQ to be at least 5x faster than django-pq. For expensive tasks taking 1/2 a second or more to complete the throughput of RQ and django-pq will be about the same. As such, django-pq is suitable for very low volume messaging or slow running task applications (see benchmarks below).

Django-pq is tested against Django 1.5, python 2.7, 3.3 with psycopg2 and pypy 2.0 with psycopg2cffi

Source repository at https://github.com/bretth/django-pq/.

Installation
--------------

.. code-block:: bash

    $ pip install django-pq

Add ``pq`` to your ``INSTALLED_APPS`` in your django settings.

You must ensure your Postgresql connections options have autocommit set to True. This is enabled by default beyond Django 1.5 but in 1.5 and earlier you should set it via ``'OPTIONS': {'autocommit': True}`` in your database settings. You may also need to set ``PQ_DEFAULT_WORKER_TTL`` if you use pooling software or your postgresql installation does not support Postgresql messaging. See `Troubleshooting Workers`_ for more.

Getting started
----------------

If you have used RQ then you’ll know django-pq but lets start with the RQ example.

.. code-block:: python

    import requests

    def count_words_at_url(url):
        resp = requests.get(url)
        return len(resp.text.split())

Create the queue.

.. code-block:: python

    from pq import Queue
    q = Queue()

Enqueue the function.

.. code-block:: python

    q.enqueue(count_words_at_url, 'http://python-rq.org')

Consume your queue with a worker.

.. code-block:: bash

    $ python manage.py pqworker --burst
    *** Listening for work on default
    Got count_words_at_url('http://python-rq.org') from default
    Job result = 818
    *** Listening for work on default


Queues
---------

Since django-pq uses django models we have one piece of syntactic sugar to maintain compatibility with RQ.

.. code-block:: python

    from pq import Queue
    # create a default queue called 'default'
    queue = Queue()

Is syntactic sugar for:

.. code-block:: python

    from  pq.queue import Queue
    queue = Queue.create()

Some more queue creation examples:

.. code-block:: python

    # name it
    q = Queue('farqueue')

    # run synchronously when settings.DEBUG == True
    from django.conf import settings

    q = Queue(async=not settings.DEBUG)

    # Up the timeout for slow jobs to 10 minutes
    q = Queue(timeout=600)

    # Connect to a different settings.DATABASES alias named 'happy-db'
    q = Queue(connection='happy-db')

Define or import a function or class method to enqueue:

.. code-block:: python

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

.. code-block:: python

    q.enqueue(say_hello, 'You')
    q.enqueue_call(say_hello, args=('You',))
    q.enqueue_call(say_call, kwargs={'name': 'You'})

    # then with a shorter timeout than 10 minutes
    q.enqueue_call(say_hello, args=('again',), timeout=60)

    #Instance methods:
    calc = Calculator(2)
    q.enqueue(calc.calculate, 4, 5)
    q.enqueue_call(calc.calculate, args=(4,5))

    # with the @job decorator
    from pq.decorators import job

    # decorate the function to be processed by the 'default' queue
    @job('default')
    def say_hello(name=None):
        """A job with a single argument and a return value."""
        if name is None:
                         name = 'Stranger'
        return 'Hi there, %s!' % (name,)

    # add a job to the queue
    job = say_hello.delay('friend')

Finally, there is a management command to enqueue from the command line:

.. code-block:: bash

    $python manage.py pqenqueue pq.utils.test_job
    $python manage.py pqenqueue test_pq.fixtures.say_hello Bob --timeout=10


Serial Queues
--------------

A serial queue exists which soft locks the queue for the task being performed. Additional tasks can be enqueued but not performed while the current task is being performed.

.. code-block:: python

    from pq import SerialQueue

    sq = SerialQueue()

A default serial queue is created called 'serial'. Serial queues are not in RQ.

Scheduling
-----------

Tasks can be scheduled at specific times, repeated at intervals, repeated until a given date, and performed in a specific time window and weekday. Unlike a cron job, a scheduled task is a promise not a guarantee to perfom a task at a specific datetime. Timezone awareness depends on your ``USE_TZ`` django setting, and the task will be performed if a worker is available and idle. Some examples:

.. code-block:: python

    from django.utils.timezone import utc, now
    from dateutil.relativedelta import relativedelta
    from datetime import datetime

    # you should use timezone aware dates if you have USE_TZ=True
    future = datetime(2014,1,1, tzinfo=utc)
    q = Queue(scheduled=True)

    # The simple enqueue like call
    q.schedule(future, say_hello, 'you')

    # A more complicated enqueue_call style version
    q.schedule_call(future, say_hello, args=('Happy New Year',), timeout=60)

    # or to repeat 10 times every 60 seconds
    q.schedule_call(now(), say_hello, args=('you & you',), repeat=10, interval=60)

    # to repeat indefinitely every day
    q.schedule_call(now(), say_hello, args=('groundhog day',), repeat=-1, interval=60*60*24)

    # ensure the schedule falls within a time range
    q.schedule_call(now(), say_hello, args=('groundhog day',),
        repeat=-1, interval=60*60*24, between='2:00/18:30')
     # could also use variants like '2.00-18.30' or '2-18:30'

    # repeat on Monday to Friday
    from dateutil.relativedelta import MO, TU, WE, TH, FR

    q.schedule_call(dt, do_nothing, repeat=-1, weekdays=(MO, TU, WE, TH, FR))
    # as integers, Monday to Wednesday
    q.schedule_call(dt, do_nothing, repeat=-1, weekdays=(0, 1, 2,))

    ## repeat on timedelta or relativedelta instances

    # repeat on the first indefinitely starting next month
    n = now()
    dt = datetime(n.year,n.month+1,1, tzinfo=utc)
    monthly = relativedelta(months=1)

    q.schedule_call(dt, say_hello, args=('groundhog day',), repeat=-1, interval=monthly)

    # or repeat on the last day of the month until 2020
    monthly = relativedelta(months=1, days=-1)
    until = datetime(2020,1,1, tzinfo=utc)

    q.schedule_call(dt, say_hello, args=('groundhog day',), repeat=until, interval=monthly)

From the commandline:

.. code-block:: bash

    # schedule now, repeat daily on Mondays and Tuesdays 
    $ ./manage.py pqschedule now package.module.func \
    --repeat=-1 --interval=86400 --mo --tu

    # schedule a one of task for the first day of 2020
    $ ./manage.py pqschedule 2020-01-01 package.module.func
    # at a specific time (any ISO8601 date/datetime)
    $ ./manage.py pqschedule 2020-01-01T9:10 package.module.func arg1 arg2 


Scheduling is a proposed feature of RQ so the api may change.

WorkFlows
----------

A simple workflow engine class ``Flow`` allows executing a specific set of tasks in sequence, each task dependent on the prior one completing.

.. code-block:: python

    from pq import Queue, Flow
    from datetime import datetime

    q = Queue()
    with Flow(q) as f:
        f.enqueue(first_task)
        f.enqueue_call(another_task, args=(1,2,3))
        f.schedule(datetime(2020,1,1), mission_to_mars)

    # or name the flow
    with Flow(q, name='myflow') as f:
        ...

    # access the job ids
    f.jobs

    # A Flow is stored in a django FlowStore instance. To retrieve them.
    fs = f.get(f.id)

    # or get a queryset of FlowStore instances by name
    fs_list = fs.get('myflow')

    # This is just a shortcut for accessing the FlowStore objects directly through the orm.
    from pq.flow import FlowStore
    fs = FlowStore.objects.get(pk=f.id)
    fs = FlowStore.objects.filter(name='myflow')

Workflows are not part of RQ.

Results
---------

By default, jobs should execute within 10 minutes. You can alter the default time in your django ``PQ_DEFAULT_JOB_TIMEOUT`` setting. After that, the worker kills the work horse and puts the job onto the failed queue, indicating the job timed out.

If a job requires more (or less) time to complete, the default timeout period can be loosened (or tightened), by specifying it as a keyword argument to the Queue.enqueue() call, like so:

.. code-block:: python

    q = Queue()
    q.enqueue(func=mytask, args=(foo,), kwargs={'bar': qux}, timeout=600)


Completed jobs hang around for a minimum TTL (time to live) of 500 seconds. Since Postgres doesn’t have an expiry option like Redis the worker will periodically poll the database for jobs to delete hence the minimum TTL. The TTL can be altered per job or through a django setting ``PQ_DEFAULT_RESULT_TTL``. If you are using workflows, a FlowStore instance has the same TTL as its final job, so they will be cleaned up too.

.. code-block:: python

    q.enqueue(func=mytask, result_ttl=0)  # out of my sight immediately
    q.enqueue(func=mytask, result_ttl=86400)  # love you long time
    q.enqueue(func=mytask, result_ttl=-1)  # together forever baby!

Workers
--------

Work is done through pqworker, a django management command. To accept work on all queues, ``$ python manage.py pqworker``.

To accept work on the fictional ``high``, ``low`` queues:

.. code-block:: bash

    $ python manage.py pqworker high low
    *** Listening for work on high, low
    Got send_newsletter('me@example.com') from default
    Job ended normally without result
    *** Listening for work on high, low

If you don’t see any output you might need to configure your django project ``LOGGING``. Here’s an example configuration that will print to the console:

.. code-block:: python

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
                'level':'INFO',
                'class':"logging.StreamHandler",
                'formatter': 'standard'
            },
        },
        'loggers': {
            'pq': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True
            },
        }
    }



Queue priority is in the order they are listed, so if the worker never finishes processing the high priority queue the other queues will never be consumed.

To exit after all work is consumed:

.. code-block:: bash

    $ ./manage.py pqworker default —-burst

More examples:

.. code-block:: bash

    $ ./manage.py pqworker default --name=doug  # change the name from the default hostname
    $ ./manage.py pqworker default --connection=[your-db-alias]  # use a different database alias instead of default
    $ ./manage.py pqworker default --sentry-dsn=SENTRY_DSN  # can also do this in settings at SENTRY_DSN


To implement a worker in code:

.. code-block:: python

    from pq import Worker
    from pq import Queue
    q = Queue()

    w = Worker(q)
    w.work(burst=True)


Troubleshooting Workers
------------------------
 
The django-pq worker depends on postgresql messaging (LISTEN and NOTIFY) to avoid polling the database. This functionality may not be available on all postgresql installations, and connection pooling may also prevent messaging from working correctly. In the event jobs are not being received instantly you can set ``PQ_DEFAULT_WORKER_TTL = 60`` to poll the database for jobs every 60 seconds. To test if your jobs will go through instantly run ``python manage.py pqworker default`` (a worker on the 'default' queue) in one terminal and a test job in another terminal, ``python manage.py pqenqueue pq.utils.test_job``.

Depending on your hosting environment down-scaling, terminating, or deploying environments with dependent worker processes may not give your workers enough time to complete their task. You can gracefully terminate all workers with a blocking command, ``./manage.py pqworker --terminate``, or use the admin to stop individual workers. In the event the worker is terminated before the job is complete, the job will remain in the dequeued admin list with a 'started' status. 


Monitoring & Admin
----------------------

Jobs are monitored or administered as necessary through the django admin. Admin actions allow jobs to be requeued or deleted.

Workers can be stopped within 1 job cycle in the admin by setting the Worker stop. 

Connections
------------

Django-pq uses the django postgresql backend in place of the RQ Redis connections, so you pass in a connection by referring to it's alias in your django DATABASES settings. Surprise surprise we use 'default' if no connection is defined.

.. code-block:: python

    q = Queue(connection='default')
    w = Worker.create(connection='default')

Workers and queues can be on different connections but workers can only work on multiple queues sharing the same connection. Workers not in burst mode recycle their connections every ``PQ_DEFAULT_WORKER_TTL`` seconds but block and listen for async notification from postgresql that a job has been enqueued.

The admin connection for job lists can be set via ``PQ_ADMIN_CONNECTION``.

Exceptions
-----------

Jobs that raise exceptions go to the ``failed`` queue. You can register a custom handler as per RQ:

.. code-block:: python

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

.. code-block:: python

    SENTRY_DSN  # as per sentry
    PQ_DEFAULT_RESULT_TTL = 500  # minumum ttl for jobs
    PQ_DEFAULT_WORKER_TTL = 420  # worker will refresh the connection (and poll the database)
    PQ_DEFAULT_JOB_TIMEOUT = 600  # jobs that exceed this time are failed
    PQ_ADMIN_CONNECTION = 'default'  # the connection to use for the admin
    PQ_QUEUE_CACHE = True # Queue is cached in local memory on creation or retrieval

Benchmarks & other lies
-------------------------

To gauge rough performance a ``pqbenchmark`` management command is included that is designed to test worker throughput while jobs are being enqueued. The command will enqueue the function ``do_nothing`` a number of times and simultaneously spawn workers to consume the benchmark queue. After enqueuing is completed a count is taken of the number of jobs remaining and an approximate number of jobs/s is calculated. There are a number of factors you can adjust to simulate your load, and as a bonus it can test RQ. For example:

.. code-block:: bash

    # Simulate trivial tasks with default settings.
    # Useful for comparing raw backend overhead.
    # 100,000 jobs and 1 worker.
    $ django-admin.py pqbenchmark

    # Simulate a slower running task.
    # Useful for seeing how many workers you can put on a task
    # Enqueue 50000 jobs with 4 workers and a 250 millisecond job execution time:
    $ django-admin.py pqbenchmark 50000 -w4 --sleep=250

    # If rq/redis is installed you can compare.
    $ django-admin.py pqbenchmark 50000 -w4 --sleep=250 --backend=rq

Starting with an unrealistic benchmark on a Macbook Pro 2.6Ghz i7 with 8GB ram and 256 GB SSD drive I get the following jobs per second throughput with Postresapp (9.2.2.0), Redis Server (2.6.11) with 100,000 enqueued jobs on default settings:

+-----------+-----------+-----------+
| Workers   | PQ-Py2.7  | RQ-Py2.7  |
+===========+===========+===========+
| 1         | 28        | 158       |
+-----------+-----------+-----------+
| 2         | 42        | 256       |
+-----------+-----------+-----------+
| 4         | 46        | 362       |
+-----------+-----------+-----------+
| 6         | 45        | 399       |
+-----------+-----------+-----------+

These results are unrealistic except to show theoretical differences between PQ and RQ. A commodity virtual server without the benefit of a local SSD for Postgresql will widen the gap dramatically between RQ and PQ, but as you can see from the numbers RQ is a far better choice for higher volumes of cheap tasks such as messaging. Unfortunately PQ needs to reset database connections between jobs which is main impediment to scaling workers.

The point of a task queue however is to process slower tasks, so simulating a slower task that has 250ms overhead (or greater) is more realistic and the task queue overhead becomes less significant, worker scaling more practical. So adjusting ``--sleep`` to 250:

+-----------+-----------+-----------+
| Workers   | PQ-Py2.7  | RQ-Py2.7  |
+===========+===========+===========+
| 1         | 3.4       | 3.9       |
+-----------+-----------+-----------+
| 2         | 6.8       | 7.8       |
+-----------+-----------+-----------+
| 4         | 13.6      | 15.3      |
+-----------+-----------+-----------+
| 6         | 17.5      | 22.8      |
+-----------+-----------+-----------+
| 10        | 33.2      | 37.6      |
+-----------+-----------+-----------+
| 20        | 44.5      | 75.9      |
+-----------+-----------+-----------+

Once your tasks get out beyond 250ms the differences between PQ and RQ become much more marginal. The important factor here are the tasks themselves, and how well your backend scales in memory usage and IO to the number of connections. Obviously again the quasi-persistent RQ is going to scale better than your average disk bound postgresql installation. In general, the slower the task the better PQ will scale connections (since it has to reset connections less often).

Development & Issues
---------------------

Contributions, questions and issues welcome on github.

Unit testing with tox, nose2 and my nose2django plugin. To run the tests, clone the repo then:

.. code-block:: bash

    $ pip install tox
    $ tox

I have been judicious about which tests were ported across from RQ, but hooray for tests. To make it easier to panel-beat smashed code django-pq does use setUp as its creator intended.

I intend to stick as closely to the documented RQ api as possible with minimal divergence.

Acknowledgements
-----------------

Without RQ (and by extension Vincent Driessen), django-pq would not exist since a fair slab of the codebase comes from that project. RQ_ is licensed according the BSD license here_.

.. _https://github.com/bretth/django-pq/: https://github.com/bretth/django-pq/
.. _RQ: http://python-rq.org
.. _here: https://raw.github.com/nvie/rq/master/LICENSE
