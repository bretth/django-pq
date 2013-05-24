/* Create the initial queues */
INSERT INTO pq_queue (name, scheduled, lock_expires, serial, idempotent)
VALUES ('default', 'true', 'January 3 04:05:06 1999 UTC', 'false', 'false');
INSERT INTO pq_queue (name, scheduled, lock_expires, serial, idempotent)
VALUES ('serial', 'true', 'January 3 04:05:06 1999 UTC', 'true', 'false');
INSERT INTO pq_queue (name, scheduled, lock_expires, serial, idempotent)
VALUES ('failed', 'false', 'January 3 04:05:06 1999 UTC', 'false', 'false');
