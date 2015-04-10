#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 2015-04-10

@author: joschi
"""
import sys
import os.path

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
