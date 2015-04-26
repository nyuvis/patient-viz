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
#import simplejson as json
import json

input_format = {}

def analyzeFile(inputFile, counter):
    idField = input_format["patient_id"]
    with open(inputFile) as csvFile:
        reader = csv.DictReader(csvFile)
        for row in reader:
            id = row[idField]
            if id in counter:
                counter[id] += 1
            else:
                counter[id] = 1

def analyzeDirectory(dir, counter):
    for (root, _, files) in os.walk(dir):
        for file in files:
            if file.endswith(".csv"):
                analyzeFile(os.path.join(root, file), counter)

def read_format(file):
    global input_format
    if not os.path.isfile(file):
        print('invalid format file: {0}'.format(file), file=sys.stderr)
        usage()
    with open(file) as formatFile:
        input_format = json.loads(formatFile.read())

def usage():
    print('usage: {0} [-h] [-m] -f <format> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-m: batch compatible output', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    human_readable = True
    starttime = time.clock()
    counter = {}
    allPaths = []
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '--':
            break
        if arg == '-h':
            usage()
        elif arg == '-m':
            human_readable = False
        elif arg == '-f':
            if not args or args[0] == "--":
                print('-f requires format file', file=sys.stderr)
                usage()
            read_format(args.pop(0))
        else:
            print('illegal argument: '+arg, file=sys.stderr)
            usage()
    while args:
        path = args.pop(0)
        if os.path.isfile(path) or path == '-':
            allPaths.append((path, True))
        elif os.path.isdir(path):
            allPaths.append((path, False))
        else:
            print('illegal argument: '+path+' is neither file nor directory', file=sys.stderr)
    if not len(allPaths):
        print('no path given', file=sys.stderr)
        usage()

    for (path, isfile) in allPaths:
        if isfile:
            analyzeFile(path, counter)
        else:
            analyzeDirectory(path, counter)

    list = counter.keys()
    list.sort(key = lambda k: counter[k])
    padding = len(str(counter[list[len(list) - 1]])) if list else 0
    total = 0
    try:
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
    except IOError as e:
        if e.errno != 32:
            raise
