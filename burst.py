#!/bin/bash
# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@"; """
from __future__ import print_function

import os
import sys
import csv
import json

import util

__doc__ = """
Created on Thu Apr 23 21:56:00 2015

@author: joschi
"""

input_format = {}

FLUSH_THRESHOLD = 100000
def writeRow(outFile, delim, doQuote, write_cache, header, row):
    if outFile not in write_cache:
        write_cache[outFile] = []
    write_cache[outFile].append(delim.join(map(lambda h: doQuote(row[h]), header)))

def flush_write_cache(delim, doQuote, write_cache, header):
    if sys.stderr.isatty():
        sys.stderr.write('\rflush cache')
    for outFile in write_cache.keys():
        lines = write_cache[outFile]
        if not os.path.isfile(outFile):
            with open(outFile, "w") as file:
                print(delim.join(map(doQuote, header)), file=file)
                for line in lines:
                    print(line, file=file)
        else:
            with open(outFile, "a") as file:
                for line in lines:
                    print(line, file=file)
    write_cache.clear()
    if sys.stderr.isatty():
        sys.stderr.write('\r           ')

def processFile(inPath, outPath, filename, out):
    delim = out['delim'];
    quote = out['quote'];

    def doQuote(cell):
        cell = str(cell)
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    write_cache = {}
    inFile = os.path.join(inPath, filename)
    print('processing {0}'.format(inFile), file=sys.stderr)
    count = 0
    with open(inFile, 'r') as csvFile:
        header = None
        for row in csv.DictReader(csvFile):
            if header is None:
                header = row.keys()
            id = row[input_format["patient_id"]]
            curPath = outPath + '/' + id[0] + '/' + id[1] + '/' + id[2]
            if not os.path.isdir(curPath):
                os.makedirs(curPath)
            outFile = os.path.join(curPath, filename)
            writeRow(outFile, delim, doQuote, write_cache, header, row)
            count += 1
            if count % 100 == 0 and sys.stderr.isatty():
                sys.stderr.write('\r{0} rows'.format(str(count)))
            if count % FLUSH_THRESHOLD == 0:
                flush_write_cache(delim, doQuote, write_cache, header)
    flush_write_cache(delim, doQuote, write_cache, header)
    if sys.stderr.isatty():
        sys.stderr.write('\r{0} rows'.format(str(count)))
        print(' -- done', file=sys.stderr)
    else:
        print('{0} rows'.format(str(count)), file=sys.stderr)
    os.remove(inFile)

### argument API

def usage():
    print('usage: {0} [-h] -f <format> -c <config> --path <path>'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print("-c <config>: specify config file", file=sys.stderr)
    print('--path <path>: a path containing input files', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    settings = {
        'delim': ',',
        'quote': '"'
    }
    path = None
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '-h':
            usage()
        if arg == '--path':
            if not args:
                print('--path requires path', file=sys.stderr)
                usage()
            path = args.pop(0)
        elif arg == '-f':
            if not args:
                print('-f requires format file', file=sys.stderr)
                usage()
            util.read_format(args.pop(0), input_format, usage)
        elif arg == '-c':
            if not args:
                print('-c requires argument', file=sys.stderr)
                usage()
            util.read_config(settings, args.pop(0))
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()
    if path is None:
        print('need to specify path with --path', file=sys.stderr)
        usage()
    if not len(input_format.keys()):
        print('need to specify non-empty format file with -f', file=sys.stderr)
        usage()
    out = {
        'delim': settings['delim'],
        'quote': settings['quote']
    }
    util.process_burst_directory(path, lambda root, file: processFile(root, path, file, out))
