#!/bin/bash
# -*- coding: utf-8 -*-
"""exec" "`dirname \"$0\"`/../call.sh" "$0" "$@"; """
from __future__ import print_function
from __future__ import division

import time as time_lib
from datetime import datetime, timedelta
import sys
import os.path
import csv
import json

sys.path.append('..')

import build_dictionary
import cms_get_patient
import util

__doc__ = """
Created on 2015-03-04

@author: joschi
"""

from_time = -float('Inf')
to_time = float('Inf')
age_time = None
age_bin = 10
ignore = {
    "prescribed": True
}
num_cutoff = 500

def toAge(s):
    # TODO there could be a more precise way
    return datetime.fromtimestamp(age_time).year - datetime.fromtimestamp(util.toTime(str(s) + "0101")).year

def handleRow(row, id, eventCache, infoCache):
    obj = {
        "info": [],
        "events": []
    }
    cms_get_patient.handleRow(row, obj)
    eventCache.extend(filter(lambda e: e['time'] >= from_time and e['time'] <= to_time and e['group'] not in ignore, obj["events"]))
    for info in obj["info"]:
        if info["id"] == "age":
            try:
                bin = (int(info["value"]) // age_bin) * age_bin
                infoCache.append("age_" + str(bin) + "_" + str(bin + age_bin))
            except ValueError:
                pass
        elif info["id"] == "born":
            try:
                if info["value"] != "N/A" and age_time is not None:
                    bin = (toAge(info["value"]) // age_bin) * age_bin
                    infoCache.append("age_" + str(bin) + "_" + str(bin + age_bin))
            except ValueError:
                pass
        elif info["id"] == "death" and info["value"] != "N/A":
            infoCache.append("dead")
        elif info["id"] == "gender":
            if info["value"] == "M":
                infoCache.append("sex_m")
            elif info["value"] == "F":
                infoCache.append("sex_f")


def processFile(inputFile, id_column, eventHandle, whitelist):
    print("processing file: {0}".format(inputFile), file=sys.stderr)
    id_event_cache = {}
    id_info_cache = {}

    def handleRows(csvDictReader):
        for row in csvDictReader:
            id = row[id_column]
            if whitelist is not None and id not in whitelist:
                continue
            if id in id_event_cache:
                eventCache = id_event_cache[id]
            else:
                eventCache = []
            if id in id_info_cache:
                infoCache = id_info_cache[id]
            else:
                infoCache = []
            handleRow(row, id, eventCache, infoCache)
            id_event_cache[id] = eventCache
            if len(infoCache) > 0:
                id_info_cache[id] = infoCache

    if inputFile == '-':
        handleRows(csv.DictReader(sys.stdin))
    else:
        with open(inputFile) as csvFile:
            handleRows(csv.DictReader(csvFile))

    eventHandle(inputFile, id_event_cache, id_info_cache)

def createEventHandler(cb):

    def handleEvent(inputFile, id_event_cache, id_info_cache):
        print("processing file: {0}".format(inputFile), file=sys.stderr)

        def processDict(events, id):
            if len(events) == 0:
                return
            #print("processing {1} with {0} events".format(len(events), id), file=sys.stderr)
            obj = {
                "events": events
            }
            dict = {}
            build_dictionary.extractEntries(dict, obj)
            for group in dict.keys():
                cb(id, group, dict[group].keys())

        num_total = len(id_event_cache.keys())
        num = 0
        for id in id_event_cache.keys():
            eventCache = id_event_cache[id]
            processDict(eventCache, id)
            del eventCache[:]
            num += 1
            if sys.stderr.isatty():
                sys.stderr.write("processing: {0:.2%}\r".format(num / num_total))
                sys.stderr.flush()
        if sys.stderr.isatty():
            print("", file=sys.stderr)
        for id in id_info_cache.keys():
            infoCache = id_info_cache[id]
            cb(id, "info", infoCache)

    return handleEvent

def emptyBitVector():
    return set([])

def getBitVector(vectors, header_list, id):
    if id in vectors:
        bitvec = vectors[id]
    else:
        bitvec = emptyBitVector()
        vectors[id] = bitvec
    return bitvec

def getHead(group, type):
    return group + "__" + type

def processAll(vectors, header_list, header_counts, path_tuples, whitelist):
    header = {}

    def handle(id, group, types):
        if "__" in group:
            print("group name is using __: {0}".format(group), file=sys.stderr)
        for type in types:
            head = getHead(group, type)
            if head not in header:
                header[head] = len(header_list)
                header_list.append(head)
            if head not in header_counts:
                header_counts[head] = 0
            else:
                header_counts[head] += 1
        bitvec = getBitVector(vectors, header_list, id)
        for type in types:
            head = getHead(group, type)
            bitvec.add(header[head])

    eventHandle = createEventHandler(handle)
    id_column = cms_get_patient.input_format["patient_id"]
    for (path, isfile) in path_tuples:
        if isfile:
            processFile(path, id_column, eventHandle, whitelist)
        else:
            util.process_directory(path, lambda file: processFile(file, id_column, eventHandle, whitelist))

def printResult(vectors, header_list, header_counts, delim, quote, whitelist, out):

    def doQuote(cell):
        cell = str(cell)
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    wkeys = whitelist.values()[0] if whitelist is not None and len(whitelist.values()) else []
    wl_header = delim + delim.join(map(lambda k: doQuote(k), wkeys)) if whitelist is not None else ""
    wl_row = lambda id: delim + delim.join(map(lambda k: doQuote(whitelist[id][k]), wkeys)) if whitelist is not None else ""

    num_total = len(vectors.keys())
    columns = []
    for (ix, h) in enumerate(header_list):
        n = header_counts[h]
        if n > num_cutoff and n < num_total - num_cutoff:
            columns.append(ix)

    s = doQuote("id") + wl_header + delim + delim.join(map(lambda c: doQuote(header_list[c]), columns))
    print(s, file=out)

    num = 0

    empty = emptyBitVector()
    for id in vectors.keys():
        bitvec = getBitVector(vectors, header_list, id)
        s = doQuote(id) + wl_row(id) + delim + delim.join(map(doQuote, map(lambda c: 1 if c in bitvec else 0, columns)))
        vectors[id] = empty
        print(s, file=out)

        num += 1
        if sys.stderr.isatty():
            sys.stderr.write("writing file: {0:.2%} complete\r".format(num / num_total))
            sys.stderr.flush()
    if sys.stderr.isatty():
        print("", file=sys.stderr)

def usage():
    print('usage: {0} [-h|--debug] [--num-cutoff <number>] [--age-time <date>] [--from <date>] [--to <date>] [-o <output>] [-w <whitelist>] -f <format> -c <config> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('--debug: prints debug output', file=sys.stderr)
    print('--num-cutoff <number>: specifies the minimum number of occurrences for a column to appear in the output. default is {0}'.format(str(num_cutoff)), file=sys.stderr)
    print('--age-time <date>: specifies the date to compute the age as "YYYYMMDD". can be omitted', file=sys.stderr)
    print('--from <date>: specifies the start date as "YYYYMMDD". can be omitted', file=sys.stderr)
    print('--to <date>: specifies the end date as "YYYYMMDD". can be omitted', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('-w <whitelist>: specifies a patient whitelist. all patients if omitted (warning: slow)', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print('-c <config>: specify config file. "-" uses default settings', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them. "-" represents stdin', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    output = '-'
    settings = build_dictionary.defaultSettings
    settings['delim'] = ','
    settings['quote'] = '"'
    whitelist = None
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '--':
            break
        if arg == '-h':
            usage()
        if arg == '--num-cutoff':
            if not args or args[0] == '--':
                print('--num-cutoff requires number', file=sys.stderr)
                usage()
            num_cutoff = int(args.pop(0))
        elif arg == '--age-time':
            if not args or args[0] == '--':
                print('--age-time requires a date', file=sys.stderr)
                usage()
            age_time = util.toTime(args.pop(0))
        elif arg == '--from':
            if not args or args[0] == '--':
                print('--from requires a date', file=sys.stderr)
                usage()
            from_time = util.toTime(args.pop(0))
        elif arg == '--to':
            if not args or args[0] == '--':
                print('--to requires a date', file=sys.stderr)
                usage()
            to_time = util.toTime(args.pop(0))
        elif arg == '-w':
            if not args or args[0] == '--':
                print('-w requires whitelist file', file=sys.stderr)
                usage()
            if whitelist is None:
                whitelist = {}
            with open(args.pop(0), 'r') as wl:
                for w in wl:
                    w = w.strip()
                    if not len(w):
                        continue
                    sw = w.split(' ')
                    whitelist[sw[0]] = {
                        "outcome": sw[1] if len(sw) > 1 else "0",
                        "test": sw[2] if len(sw) > 2 else "0",
                    }
        elif arg == '-f':
            if not args or args[0] == '--':
                print('-f requires format file', file=sys.stderr)
                usage()
            util.read_format(args.pop(0), cms_get_patient.input_format, usage)
        elif arg == '-o':
            if not args or args[0] == '--':
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
        elif arg == '-c':
            if not args or args[0] == '--':
                print('-c requires argument', file=sys.stderr)
                usage()
            util.readConfig(settings, args.pop(0), build_dictionary.debugOutput)
        elif arg == '--debug':
            build_dictionary.debugOutput = True
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    build_dictionary.setPathCorrection('../')
    build_dictionary.reportMissingEntries = False
    build_dictionary.init(settings)

    allPaths = []
    while args:
        path = args.pop(0)
        if os.path.isfile(path) or path == '-':
            allPaths.append((path, True))
        elif os.path.isdir(path):
            allPaths.append((path, False))
        else:
            print('illegal argument: '+path+' is neither file nor directory', file=sys.stderr)

    vectors = {}
    header_list = []
    header_counts = {}
    processAll(vectors, header_list, header_counts, allPaths, whitelist)
    with util.OutWrapper(output) as out:
        printResult(vectors, header_list, header_counts, settings['delim'], settings['quote'], whitelist, out)
