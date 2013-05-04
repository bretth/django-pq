# -*- coding: utf-8 -*-
"""
Miscellaneous helper functions.

The formatter for ANSI colored console output is heavily based on Pygments
terminal colorizing code, originally by Georg Brandl.
"""
import os
import re
import sys
import logging
from datetime import timedelta, datetime, time
from dateutil import relativedelta
from six import integer_types

from .compat import is_python_version
from .exceptions import InvalidBetween, InvalidWeekdays


def gettermsize():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct  # noqa
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])

def get_restricted_datetime(at, between='', weekdays=None):
    """
    Returns a new datetime that always falls in
    the timerange ``between`` an iso 8601 string or variant,
    and days where days is a list or tuple of relativedelta weekday
    objects.

    If the time part of the datetime falls before the
    timerange the datetime will be moved forward to the
    start of the range. In the event the time is after the
    range the datetime will be moved forward to the next
    day.

    >>> dt = datetime(2013,1,1,6,30)
    >>> get_restricted_datetime(dt, '7-12')
    datetime(2013,1,1,7)
    >>> get_restricted_datetime(dt, '1:00/6:00')
    datetime(2013,1,2,1)
    >>> get_restricted_datetime(dt, '1:00-6:00')
    datetime(2013,1,2,1)
    >>> get_restricted_datetime(dt, '1:00:10/6:00:59')
    datetime(2013,1,2,1)
    """
    if between:
        pattern = re.compile(
            r"(\d{1,2})[:.]?(\d{0,2})[:.]?\d{0,2}\s*[/-]+" +
            r"\s*(\d{1,2})[:.]?(\d{0,2})[:.]?\d{0,2}"
            )
        r = pattern.search(between)
        if not r:
            raise InvalidBetween("Invalid between range %s" % between)

        shour, smin, ehour, emin = r.groups()
        shour = int(shour)
        smin = int(smin) if smin else 0
        ehour = int(ehour)
        emin = int(emin) if emin else 0
        if ehour < shour:
            raise InvalidBetween("Between end cannot be before start")
        elif ehour == 24:
            ehour = 23
            emin = 59
        st = time(shour, smin, tzinfo=at.tzinfo)
        et = time(ehour, emin, tzinfo=at.tzinfo)
        date = at.date()
        compare_st = datetime.combine(date, st)
        compare_et = datetime.combine(date, et)
        if at < compare_st:
            at = compare_st
        elif at > compare_et:
            at = compare_st + timedelta(days=1)
    if weekdays:
        weekdays = list(weekdays)
        for i, value in enumerate(weekdays):
            if isinstance(value, relativedelta.weekday):
                weekdays[i] = value.weekday
            elif isinstance(value, integer_types) and value >=0 and value <=6:
                continue
            else:
                msg = "Invalid weekday %s. Weekdays must be a" % str(value)
                msg = ' '.join([msg, "list or tuple of relativedelta.weekday",
                               "instances or integers between 0 and 6"])
                raise InvalidWeekdays(msg)
        weekdays = sorted(weekdays)
        nextdays = relativedelta.weekdays[at.weekday():]
        priordays = relativedelta.weekdays[:at.weekday()]
        for i, day in enumerate(nextdays + priordays):
            if day.weekday in weekdays:
                at += timedelta(days=i)
                break
    return at


class _Colorizer(object):
    def __init__(self):
        esc = "\x1b["

        self.codes = {}
        self.codes[""] = ""
        self.codes["reset"] = esc + "39;49;00m"

        self.codes["bold"] = esc + "01m"
        self.codes["faint"] = esc + "02m"
        self.codes["standout"] = esc + "03m"
        self.codes["underline"] = esc + "04m"
        self.codes["blink"] = esc + "05m"
        self.codes["overline"] = esc + "06m"

        dark_colors = ["black", "darkred", "darkgreen", "brown", "darkblue",
                        "purple", "teal", "lightgray"]
        light_colors = ["darkgray", "red", "green", "yellow", "blue",
                        "fuchsia", "turquoise", "white"]

        x = 30
        for d, l in zip(dark_colors, light_colors):
            self.codes[d] = esc + "%im" % x
            self.codes[l] = esc + "%i;01m" % x
            x += 1

        del d, l, x

        self.codes["darkteal"] = self.codes["turquoise"]
        self.codes["darkyellow"] = self.codes["brown"]
        self.codes["fuscia"] = self.codes["fuchsia"]
        self.codes["white"] = self.codes["bold"]
        self.notty = not sys.stdout.isatty()


    def reset_color(self):
        return self.codes["reset"]

    def colorize(self, color_key, text):
        if not sys.stdout.isatty():
            return text
        else:
            return self.codes[color_key] + text + self.codes["reset"]

    def ansiformat(self, attr, text):
        """
        Format ``text`` with a color and/or some attributes::

            color       normal color
            *color*     bold color
            _color_     underlined color
            +color+     blinking color
        """
        result = []
        if attr[:1] == attr[-1:] == '+':
            result.append(self.codes['blink'])
            attr = attr[1:-1]
        if attr[:1] == attr[-1:] == '*':
            result.append(self.codes['bold'])
            attr = attr[1:-1]
        if attr[:1] == attr[-1:] == '_':
            result.append(self.codes['underline'])
            attr = attr[1:-1]
        result.append(self.codes[attr])
        result.append(text)
        result.append(self.codes['reset'])
        return ''.join(result)


colorizer = _Colorizer()


def make_colorizer(color):
    """Creates a function that colorizes text with the given color.

    For example:

        green = make_colorizer('darkgreen')
        red = make_colorizer('red')

    Then, you can use:

        print "It's either " + green('OK') + ' or ' + red('Oops')
    """
    def inner(text):
        return colorizer.colorize(color, text)
    return inner


class ColorizingStreamHandler(logging.StreamHandler):

    levels = {
        logging.WARNING: make_colorizer('darkyellow'),
        logging.ERROR: make_colorizer('darkred'),
        logging.CRITICAL: make_colorizer('darkred'),
    }

    def __init__(self, exclude=None, *args, **kwargs):
        self.exclude = exclude
        if is_python_version((2,6)):
            logging.StreamHandler.__init__(self, *args, **kwargs)
        else:
            super(ColorizingStreamHandler, self).__init__(*args, **kwargs)

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            colorize = self.levels.get(record.levelno, lambda x: x)

            # Don't colorize any traceback
            parts = message.split('\n', 1)
            parts[0] = " ".join([parts[0].split(" ", 1)[0], colorize(parts[0].split(" ", 1)[1])])

            message = '\n'.join(parts)

        return message

def test_job():
    """ A simple do nothing test job """
    print('Hello world')