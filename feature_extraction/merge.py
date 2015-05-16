#!/bin/bash
# -*- coding: utf-8 -*-
"""exec" "`dirname \"$0\"`/../call.sh" "$0" "$@"; """
from __future__ import print_function

import time as time_lib
from datetime import datetime, timedelta
import sys
import os.path
import csv
import random

sys.path.append('..')

import util

__doc__ = """
Created on 2015-04-10

@author: joschi
"""

def doMerge(input, casesFlag, testPerc, sanity, out):
    with open(input, 'r') as fin:
        for line in fin:
            line = line.strip()
            if " " in line:
                raise ValueError("id contains ' ': '{0}' file: {1}".format(line, input))
            isTest = testPerc > random.random() * 100
            print("{0} {1} {2}".format(line, casesFlag, "1" if isTest else "0"), file=out)
            if line in sanity:
                if sanity[line] == casesFlag:
                    print("warning! duplicate id: {0}".format(line), file=sys.stderr)
                else:
                    print("warning! same id in cases and controls: {0}".format(line), file=sys.stderr)
            sanity[line] = casesFlag

def usage():
    print('usage: {0} [-h] --cases <cohort file> --control <cohort file> [-o <output>] [--test <percentage>] [--seed <seed>]'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('--cases <cohort file>: specifies the case cohort', file=sys.stderr)
    print('--control <cohort file>: specifies the control cohort', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('--test <percentage>: specifies the percentage (0-100) of patients used for verifying the model. default is 0', file=sys.stderr)
    print('--seed <seed>: specifies the seed for the rng. if omitted the seed is not set', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    output = '-'
    seed = None
    testPerc = 0
    control = ""
    cases = ""
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '--':
            break
        if arg == '-h':
            usage()
        if arg == '-o':
            if not len(args):
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
        elif arg == '--cases':
            if not len(args):
                print('--cases requires cohort file', file=sys.stderr)
                usage()
            cases = args.pop(0)
        elif arg == '--control':
            if not len(args):
                print('--control requires cohort file', file=sys.stderr)
                usage()
            control = args.pop(0)
        elif arg == '--test':
            if not len(args):
                print('--test requires percentage', file=sys.stderr)
                usage()
            testPerc = float(args.pop(0))
        elif arg == '--seed':
            if not len(args):
                print('--seed requires seed', file=sys.stderr)
                usage()
            seed = args.pop(0)
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    if not len(cases) or not len(control):
        print('requires cases and control cohorts')
        usage()

    random.seed(seed)

    sanity = {}
    with util.OutWrapper(output) as out:
        doMerge(cases, "1", testPerc, sanity, out)
        doMerge(control, "0", testPerc, sanity, out)
