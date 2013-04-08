import unittest
from datetime import datetime

from django.utils.timezone import utc
from nose2.tools import params
from dateutil.relativedelta import weekdays

from pq.utils import get_restricted_datetime
from pq.exceptions import InvalidWeekdays

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


class TestGetRestrictedDatetimeWeekdays(unittest.TestCase):
    def setUp(self):
        self.dt = datetime(2013, 1, 1)

    @params(
        ((1,), datetime(2013,1,1)),
        ((0,), datetime(2013,1,7)),
        ((weekdays[6],weekdays[5]), datetime(2013,1,5)),
    )
    def test_get_restricted_weekdays(self, weekdays, result):
        dt = get_restricted_datetime(self.dt, weekdays=weekdays)
        self.assertEqual(dt, result)

    def test_invalid_weekdays(self):
        with self.assertRaises(InvalidWeekdays):
            dt = get_restricted_datetime(self.dt, weekdays=(7,))


