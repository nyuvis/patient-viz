# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@"; """
from __future__ import print_function
from __future__ import division

import sys
import os
from datetime import datetime, timedelta, tzinfo
import pytz
import collections
from operator import itemgetter
import json

__doc__ = """
Created on 2015-04-10

@author: joschi
"""

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
    return not isinstance(v, str) and (isinstance(v, list) or isinstance(v, collections.Sequence))

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

_path_correction = '.'
def get_file(file, debugOutput=False):
    res = os.path.join(_path_correction, file)
    if debugOutput:
        print("exists: {0} file: {1}".format(repr(os.path.isfile(res)), repr(os.path.abspath(res))), file=sys.stderr)
    return res

def read_config(settings, file, debugOutput=False):
    global _path_correction
    if file is None:
        return
    _path_correction = os.path.dirname(os.path.abspath(file))
    config = {}
    if debugOutput:
        print("config exists: {0} file: {1}".format(repr(os.path.isfile(file)), repr(os.path.abspath(file))), file=sys.stderr)
    if os.path.isfile(file):
        with open(file, 'r') as input:
            config = json.loads(input.read())
    settings.update(config)
    if not set(settings.keys()) - set(config.keys()):
        return
    same = True
    for k in settings.keys():
        if settings[k] != config[k]:
            same = False
            break
    if not same:
        with open(file, 'w') as output:
            print(json.dumps(settings, indent=2, sort_keys=True), file=output)

def read_format(file, input_format, usage):
    if not os.path.isfile(file):
        print('invalid format file: {0}'.format(file), file=sys.stderr)
        usage()
    with open(file) as formatFile:
        input_format.update(json.loads(formatFile.read()))

def process_burst_directory(dir, cb):
    for (root, _, files) in sorted(os.walk(dir), key=itemgetter(0)):
        if root != dir:
            continue
        for file in sorted(files):
            if file.endswith(".csv"):
                cb(root, file)

def process_directory(dir, cb, show_progress=True):
    dirty = False
    for (root, _, files) in sorted(os.walk(dir), key=itemgetter(0)):
        if root != dir:
            segs = root.split('/') # **/A/4/2/*.csv
            if len(segs) >= 4:
                segs = segs[-3:]
                if (
                        len(segs[0]) == 1 and
                        len(segs[1]) == 1 and
                        len(segs[2]) == 1
                    ):
                    if show_progress and sys.stderr.isatty():
                        try:
                            progr = (int(segs[0], 16)*16*16 + int(segs[1], 16)*16 + int(segs[2], 16)) / (16**3 - 1)
                            sys.stderr.write("processing: {0}/{1}/{2}/ {3:.2%}\r".format(segs[0], segs[1], segs[2], progr))
                            sys.stderr.flush()
                            dirty = True
                        except:
                            pass
                    for file in sorted(files):
                        if file.endswith(".csv"):
                            cb(os.path.join(root, file), False)
                    continue
        for file in sorted(files):
            if file.endswith(".csv"):
                if dirty and show_progress and sys.stderr.isatty():
                    print("", file=sys.stderr)
                    dirty = False
                cb(os.path.join(root, file), show_progress)
    if dirty and show_progress and sys.stderr.isatty():
        print("", file=sys.stderr)


def process_id_directory(dir, id, cb):
    for (root, _, files) in sorted(os.walk(dir), key=itemgetter(0)):
        if root != dir:
            segs = root.split('/') # **/A/4/2/*.csv
            if len(segs) >= 4:
                segs = segs[-3:]
                if (
                        len(segs[0]) == 1 and
                        len(segs[1]) == 1 and
                        len(segs[2]) == 1 and
                        (
                            segs[0][0] != id[0] or
                            segs[1][0] != id[1] or
                            segs[2][0] != id[2]
                        )
                    ):
                    continue
        for file in sorted(files):
            if file.endswith(".csv"):
                cb(os.path.join(root, file), id)

