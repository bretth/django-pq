django-pq
==========

When complete, PQ will be a task queue based on the elegant [RQ](http://python-rq.org) api with a postgresql backend.

RQ sets a low barrier for entry, and django-pq takes it lower for sites that can’t or don’t want to use Redis in their stack, and are happy to trade off performance for the transactional integrity of Postgres. As additional throughput is required you should be able to switch out or mix PQ with the more performant Redis based RQ with only trival code changes.

Installation
--------------

    $ pip install django-pq

Getting started
----------------

If you have used RQ the api is almost identical.

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

    $ pqworker
