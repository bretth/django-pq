import unittest
from datetime import datetime

from django.utils.timezone import utc
from nose2.tools import params

from pq.utils import get_restricted_datetime


class TestGetRestrictedDatetime(unittest.TestCase):
    def setUp(self):
        self.dt = datetime(2013, 1, 1, 6, tzinfo=utc)

    @params(
        ('0-24', datetime(2013,1,1,6, tzinfo=utc)),
        ('1.30 - 5.30', datetime(2013,1,2,1,30, tzinfo=utc)),
        ('7:00-8:00', datetime(2013,1,1,7,0, tzinfo=utc)),
        ('7:00/8:00', datetime(2013,1,1,7,0, tzinfo=utc)),
        ('7:00:01-8:00:59', datetime(2013,1,1,7,0, tzinfo=utc)),


    )
    def test_get_restricted_datetime(self, between, result):
        dt = get_restricted_datetime(self.dt, between)
        self.assertEqual(dt, result)

    def test_get_naive_datetime(self):
        dt = datetime(2013,1,1,6)
        rdt = get_restricted_datetime(dt, '0-24')
        self.assertEqual(dt, rdt)



