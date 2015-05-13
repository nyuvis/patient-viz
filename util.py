#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 2015-04-10

@author: joschi
"""
import sys
import os
from datetime import datetime, timedelta, tzinfo
import pytz

_compute_self = "total_seconds" not in dir(timedelta(seconds=1))
_tz = pytz.timezone('US/Eastern')
_epoch = datetime(year=1970, month=1, day=1, tzinfo=_tz)
_day_seconds = 24 * 3600
_milli = 10**6
def _mktime(dt):
    if not _compute_self:
        res = (dt - _epoch).total_seconds()
    else:
        td = dt - _epoch
        res = (td.microseconds + (td.seconds + td.days * _day_seconds) * _milli) / _milli
    return int(res - res % _day_seconds)

def toTime(s):
    return _mktime(datetime(year=int(s[0:4]), month=int(s[4:6]), day=int(s[6:8]), tzinfo=_tz))

def nextDay(stamp):
    return _mktime(_epoch + timedelta(days=1, seconds=stamp))

def is_array(v):
    try:
        if isinstance(v, unicode):
            return False
    except NameError:
        pass
    return not isinstance(v, str) and isinstance(v, collections.Sequence)

class StdOutClose(Exception): pass

class OutWrapper(object):
    def __init__(self, filename):
        self._isStdout = filename == '-'
        self._fp = open(filename, 'w') if not self._isStdout else sys.stdout
        self._still_open = True

    def write(self, data):
        if not self._still_open:
            return
        try:
            self._fp.write(data)
        except IOError as e:
            if self._isStdout and e.errno == 32:
                self._still_open = False
                raise StdOutClose()
            else:
                raise

    def flush(self):
        if not self._still_open:
            return
        try:
            self._fp.flush()
        except IOError as e:
            if self._isStdout and e.errno == 32:
                self._still_open = False
                raise StdOutClose()
            else:
                raise

    def close(self):
        if self._still_open:
            self._fp.close()
            self._still_open = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        return isinstance(value, StdOutClose)
