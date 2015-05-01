#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 2015-04-10

@author: joschi
"""
import sys
import os
import time
from datetime import datetime, timedelta

# fix timezone -- doesn't really matter since the granularity is days
os.environ['TZ'] = 'UTC-0400'
time.tzset()

def _mktime(dt):
    try:
        return int(time.mktime(dt.timetuple()))
    except OverflowError:
        epoch = datetime(1970, 1, 1)
        diff = dt - epoch
        return diff.days * 24 * 3600 + diff.seconds

def toTime(s):
    return _mktime(datetime.strptime(s, "%Y%m%d"))

def nextDay(stamp):
    return _mktime(datetime.fromtimestamp(stamp) + timedelta(days = 1))

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
        if not self._isStdout and self._still_open:
            self._fp.close()
            self._still_open = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        return isinstance(value, StdOutClose)
