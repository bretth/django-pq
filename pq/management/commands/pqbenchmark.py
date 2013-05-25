
import time
from django.core.management.base import BaseCommand
from optparse import make_option

def do_nothing(sleep=0):
    """The best job in the world."""
    if sleep:
        time.sleep(sleep/1000.0)

def worker(worker_num, backend):
    import subprocess
    print('Worker %i started' % worker_num)
    if backend == 'pq':
        subprocess.call('django-admin.py pqworker benchmark -b', 
            shell=True)
    elif backend == 'rq':
        from rq.worker import Worker
        from redis import Redis
        from rq import Queue
        q = Queue('benchmark', connection=Redis())
        w = Worker(q, connection=Redis())
        w.work(burst=False)
    print('Worker %i fin' % worker_num)
    return


def feeder(num_jobs, backend, sleep):
    if backend == 'pq':
        from pq import Queue
        q = Queue('benchmark')
    elif backend == 'rq':
        from redis import Redis
        from rq import Queue
        connection=Redis()
        q = Queue('benchmark', connection=Redis())
    print('enqueuing %i jobs'% num_jobs)
    for i in range(num_jobs):
        q.enqueue(do_nothing, sleep)
    print('feeder fin')    


class Command(BaseCommand):
    help = "Benchmarks PQ and RQ"
    args = "<number of jobs>"

    option_list = BaseCommand.option_list + (
        make_option('--workers', '-w', default=1, dest='workers',
            help='Number of workers [1]'),
        make_option('--backend', '-b', default='pq', dest='backend',
            help='Backend to use [pq] or rq'),
        make_option('--sleep', default=0, dest='sleep',
            help='Add sleep milliseconds to job [0]')
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        import multiprocessing
        import time
        backend = options.get('backend')
        if backend.lower() == 'pq':
            from pq import Queue
            from pq.job import Job
            q = Queue('benchmark')
            Job.objects.filter(queue_id='benchmark').delete()
        elif backend.lower() == 'rq':
            from redis import Redis
            from rq import Queue
            connection=Redis()
            q = Queue('benchmark', connection=Redis())
        q.empty()
        print('Init queue count: %i' % q.count)
        num_workers = int(options.get('workers'))
        sleep = int(options.get('sleep'))
        try:
            num_jobs = int(args[0])
        except IndexError:
            num_jobs = 100000 
        eq = multiprocessing.Process(target=feeder, args=(num_jobs, backend, sleep), name=str('Feeder'))
        eq.start()
        workers = []
        
        start = time.time()
        for i in range(num_workers):
            p = multiprocessing.Process(target=worker, args=(i, backend), name=str('Worker %i' % i))
            workers.append(p)
            p.start()
        eq.join()
        count = q.count
        stop = time.time()
        q.empty()

        for i, j in enumerate(workers):
            print('Terminating worker %s' % i)
            j.terminate()

        print('Fin queue count %i'% count)
        num_jobs = num_jobs - count
        total_time = stop - start
        print('Total time %s seconds' % str(total_time))
        print('Jobs completed: %i' % num_jobs)
        
        jobs_per_sec = round(num_jobs/total_time, 1)
        print('%s jobs/s' % str(jobs_per_sec))
