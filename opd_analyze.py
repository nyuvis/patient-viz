#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 20 11:55:00 2015

@author: joschi
"""
from __future__ import print_function
import time
import os
import sys
import csv

idField = 'DESYNPUF_ID'

def analyzeFile(inputFile, counter):
    with open(inputFile) as csvFile:
        reader = csv.DictReader(csvFile)
        for row in reader:
            id = row[idField]
            if id in counter:
                counter[id] += 1
            else:
                counter[id] = 1

def analyzeDirectory(dir, counter):
    for (_, _, files) in os.walk(dir):
        for file in files:
            if file.endswith(".csv"):
                analyzeFile(dir + '/' + file, counter)

def usage():
    print('usage: {0} [-h] [-m] <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-m: batch compatible output', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    has_path = False
    human_readable = True
    starttime = time.clock()
    counter = {}
    args = sys.argv[:]
    args.pop(0)
    while args:
        path = args.pop(0)
        if path == '-h':
            usage()
        elif path == '-m':
            human_readable = False
        elif os.path.isfile(path):
            analyzeFile(path, counter)
            has_path = True
        elif os.path.isdir(path):
            analyzeDirectory(path, counter)
            has_path = True
        else:
            print('illegal argument: '+path+' is neither file nor directory', file=sys.stderr)
            usage()
    if not has_path:
        print('warning: no path given', file=sys.stderr)
    list = counter.keys()
    list.sort(key = lambda k: counter[k])
    padding = len(str(counter[list[len(list) - 1]])) if list else 0
    total = 0
    for id in list:
        num = counter[id]
        total += num
        if human_readable:
            print('{0:{width}}'.format(num, width=padding) + ' ' + id, file=sys.stdout)
        else:
            print(id, file=sys.stdout)
    if human_readable:
        print('', file=sys.stdout)
        print('time: '+str(time.clock() - starttime)+'s', file=sys.stdout)
        print('ids: '+str(len(list)), file=sys.stdout)
        print('entries: '+str(total), file=sys.stdout)
        print('mean: '+str(total / len(list)), file=sys.stdout)
