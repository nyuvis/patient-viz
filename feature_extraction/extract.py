# -*- coding: utf-8 -*-
# -*- mode: python; -*-
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
age_bin_count = 10
ignore = {
    "prescribed": True,
    "provider": True,
    "physician": True
}
num_cutoff = 500
show_progress = True

class Dispatcher():
    def __init__(self):
        self._info_collect = {}
        self._aggregators = {}

    def info_collector(self, column_prefixes):
        prefix = "collect_"
        def wrapper(fun):
            name = fun.__name__
            if not name.startswith(prefix):
                raise ValueError("info collector {0} must start with {1}".format(name, prefix))
            name = name[len(prefix):]
            if name in self._info_collect:
                raise ValueError("info collector already defined for {0}".format(name))
            self._info_collect[name] = (fun, [ "info__{0}".format(cp) for cp in column_prefixes ])
            return fun
        return wrapper

    def get_info_collector(self, name):
        return self._info_collect[name]

    def aggregator(self, default_value):
        prefix = "aggr_"
        def wrapper(fun):
            method_name = fun.__name__
            if not method_name.startswith(prefix):
                raise ValueError("aggregator method {0} must start with {1}".format(method_name, prefix))
            method_name = method_name[len(prefix):]
            if method_name in self._aggregators:
                raise ValueError("aggregator method {0} already defined".format(method_name))
            self._aggregators[method_name] = (fun, default_value)
            return fun
        return wrapper

    def get_aggregator(self, name):
        if name not in self._aggregators:
            raise ValueError("unknown aggregator {0}".format(name))
        return self._aggregators[name]

dispatch = Dispatcher()

class ColumnHandler:
    def __init__(self, dispatch, default_aggr):
        self._dispatch = dispatch
        self._info_collectors = []
        self._column_prefixes = []
        self._columns = {}
        self._valid_levels = None
        aggr_fun, default_value = dispatch.get_aggregator(default_aggr)
        self._default_aggr = (aggr_fun, default_value, default_aggr)

    def add_info_handler(self, collector, aggregator):
        collector_fun, column_prefixes = self._dispatch.get_info_collector(collector)
        aggr_fun, default_value = self._dispatch.get_aggregator(aggregator)
        self._info_collectors.append(collector_fun)
        for cp in column_prefixes:
            for (ocp, _, _, _) in self._column_prefixes:
                if cp.startswith(ocp) or ocp.startswith(cp):
                    raise ValueError("column prefixes shadow each other: {0} {1}".format(cp, ocp))
            self._column_prefixes.append((cp, aggr_fun, default_value, aggregator))

    def get_info_collectors(self):
        return self._info_collectors

    def get_column_aggregator(self, column):
        if column not in self._columns:
            for (cp, aggr_fun, default_value, name) in self._column_prefixes:
                if column.startswith(cp):
                    self._columns[column] = (aggr_fun, default_value, name)
                    break
        if column not in self._columns:
            self._columns[column] = self._default_aggr
        return self._columns[column]

    def set_valid_levels(self, vl):
        self._valid_levels = vl

    def valid_levels(self):
        return self._valid_levels

### aggregators ###

@dispatch.aggregator(0)
def aggr_binary(_aggr, _cur):
    return 1

@dispatch.aggregator(0)
def aggr_count(aggr, _cur):
    return aggr + 1

@dispatch.aggregator(0)
def aggr_sum(aggr, cur):
    return aggr + cur

@dispatch.aggregator(0)
def aggr_max(aggr, cur):
    return max(aggr, cur)

@dispatch.aggregator(0)
def aggr_unique(aggr, cur):
    if aggr != 0 and cur != aggr:
        raise ValueError("multiple unique values {0} and {1}".format(aggr, cur))
    return cur

### info collectors ###

@dispatch.info_collector([ "age_" ])
def collect_age_bin(info, infoCache):
    if info["id"] == "born":
        try:
            bin = (int(info["value"]) // age_bin_count) * age_bin_count
            infoCache.append(("age_" + str(bin) + "_" + str(bin + age_bin_count), 1))
        except ValueError:
            pass
    elif info["id"] == "age":
        try:
            if info["value"] != "N/A" and age_time is not None:
                bin = (util.toAge(info["value"], age_time) // age_bin_count) * age_bin_count
                infoCache.append(("age_" + str(bin) + "_" + str(bin + age_bin_count), 1))
        except ValueError:
            pass

@dispatch.info_collector([ "age" ])
def collect_age_field(info, infoCache):
    if info["id"] == "born":
        try:
            infoCache.append(("age", int(info["value"])))
        except ValueError:
            pass
    elif info["id"] == "age":
        try:
            if info["value"] != "N/A" and age_time is not None:
                infoCache.append(("age", util.toAge(info["value"], age_time)))
        except ValueError:
            pass

@dispatch.info_collector([ "dead" ])
def collect_dead_field(info, infoCache):
    if info["id"] == "death":
        infoCache.append(("dead", 1 if info["value"] != "N/A" else 0))

@dispatch.info_collector([ "sex_" ])
def collect_sex_field(info, infoCache):
    if info["id"] == "gender":
        if info["value"] == "M":
            infoCache.append(("sex_m", 1))
        elif info["value"] == "F":
            infoCache.append(("sex_f", 1))

@dispatch.info_collector([ "gender" ])
def collect_gender_field(info, infoCache):
    if info["id"] == "gender":
        if info["value"] == "M":
            infoCache.append(("gender", 1))
        elif info["value"] == "F":
            infoCache.append(("gender", 2))

@dispatch.info_collector([ "hospital_days" ])
def collect_hospital_days(info, infoCache):
    if info["id"] == "stay_in_hospital":
        infoCache.append(("hospital_days", info["value"]))

### vector handling ###

def emptyBitVector():
    return {}

def addToBitVector(vector, c, ch, type, value):
    aggr_fun, default_value, _ = ch.get_column_aggregator(type)
    vector[c] = aggr_fun(vector.get(c, default_value), value)

def showVectorValue(vector, c, type, ch):
    _, default_value, _ = ch.get_column_aggregator(type)
    return str(vector.get(c, default_value))

def getBitVector(vectors, header_list, id):
    if id in vectors:
        bitvec = vectors[id]
    else:
        bitvec = emptyBitVector()
        vectors[id] = bitvec
    return bitvec

def getHead(group, type):
    return group + "__" + type

### reading rows ###

def handleRow(inputFile, row, id, eventCache, infoCache, ch):
    obj = {
        "info": [],
        "events": []
    }
    status_map = {}
    status = cms_get_patient.STATUS_UNKNOWN
    # inputFile is already lower case
    if "inpatient" in inputFile:
        status = cms_get_patient.STATUS_IN
    elif "outpatient" in inputFile:
        status = cms_get_patient.STATUS_OUT
    cms_get_patient.handleRow(row, obj, status_map, status)
    spans = []
    cms_get_patient.add_status_intervals(status_map, spans)
    obj["info"].extend([ {
        'id': 'stay_' + s["class"],
        'value': util.span_to_days(s["to"] - s["from"])
    } for s in spans ])
    eventCache.extend(filter(lambda e: e['time'] >= from_time and e['time'] <= to_time and e['group'] not in ignore, obj["events"]))
    for info in obj["info"]:
        for ic in ch.get_info_collectors():
            ic(info, infoCache)

def processFile(inputFile, id_column, eventHandle, whitelist, ch, printInfo):
    id_event_cache = {}
    id_info_cache = {}

    def handleRows(csvDictReader, inputFile):
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
            handleRow(inputFile, row, id, eventCache, infoCache, ch)
            id_event_cache[id] = eventCache
            if len(infoCache) > 0:
                id_info_cache[id] = infoCache

    if inputFile == '-':
        handleRows(csv.DictReader(sys.stdin), '-')
    else:
        with open(inputFile) as csvFile:
            handleRows(csv.DictReader(csvFile), inputFile.lower())

    eventHandle(inputFile, id_event_cache, id_info_cache, printInfo)

def createEventHandler(cb, valid_levels):

    def get_real(group, e):
        if "alias" in e and e["alias"] and e["alias"] != e["id"] and e["alias"] in group:
            return get_real(group[e["alias"]])
        return e

    def is_valid_level(group, e):
        if valid_levels is None:
            return True
        level = 0
        while e["parent"]:
            e = get_real(group, group[e["parent"]])
            level += 1
        return level in valid_levels

    def handleEvent(inputFile, id_event_cache, id_info_cache, printInfo):
        if printInfo:
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
                cur_group = dict[group]
                ekeys = set([])
                for ek in cur_group.keys():
                    event = get_real(cur_group, cur_group[ek])
                    if is_valid_level(cur_group, event):
                        ekeys.add(event["id"])
                cb(id, group, [ (k, 1) for k in ekeys ])

        num_total = len(id_event_cache.keys())
        num = 0
        for id in id_event_cache.keys():
            eventCache = id_event_cache[id]
            processDict(eventCache, id)
            del eventCache[:]
            num += 1
            if printInfo and sys.stderr.isatty():
                sys.stderr.write("processing: {0:.2%}\r".format(num / num_total))
                sys.stderr.flush()
        if printInfo and sys.stderr.isatty():
            print("", file=sys.stderr)
        for id in id_info_cache.keys():
            infoCache = id_info_cache[id]
            cb(id, "info", infoCache)

    return handleEvent

def processAll(vectors, header_list, header_counts, path_tuples, whitelist, ch):
    header = {}

    def handle(id, group, types):
        if "__" in group:
            print("group name is using __: {0}".format(group), file=sys.stderr)
        for type, _ in types:
            head = getHead(group, type)
            if head not in header:
                header[head] = len(header_list)
                header_list.append(head)
            if head not in header_counts:
                header_counts[head] = 0
            else:
                header_counts[head] += 1
        bitvec = getBitVector(vectors, header_list, id)
        for type, value in types:
            head = getHead(group, type)
            addToBitVector(bitvec, header[head], ch, head, value)

    eventHandle = createEventHandler(handle, ch.valid_levels())
    id_column = cms_get_patient.input_format["patient_id"]
    for (path, isfile) in path_tuples:
        if isfile:
            processFile(path, id_column, eventHandle, whitelist, ch, show_progress)
        else:
            util.process_whitelisted_directory(path, whitelist, lambda file, printInfo: processFile(file, id_column, eventHandle, whitelist, ch, printInfo), show_progress=show_progress)

def printResult(vectors, hl, header_counts, delim, quote, whitelist, ch, out):

    def doQuote(cell):
        cell = str(cell)
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    wkeys = whitelist.values()[0] if whitelist is not None and len(whitelist.values()) else []
    wl_header = delim + delim.join(map(lambda k: doQuote(k), wkeys)) if whitelist is not None else ""
    wl_row = lambda id: delim + delim.join(map(lambda k: doQuote(whitelist[id][k]), wkeys)) if whitelist is not None else ""

    num_total = len(vectors.keys())
    columnMap = {}
    for (ix, h) in enumerate(hl):
        n = header_counts[h]
        _, _, name = ch.get_column_aggregator(h)
        if name != "binary" or num_cutoff < 0 or (n > num_cutoff and n < num_total - num_cutoff):
            columnMap[h] = ix

    columns = map(lambda h: columnMap[h], sorted(columnMap.keys()))

    s = doQuote("id") + wl_header + delim + delim.join(map(lambda c: doQuote(hl[c]), columns))
    print(s, file=out)

    num = 0

    empty = emptyBitVector()
    for id in vectors.keys():
        bitvec = getBitVector(vectors, hl, id)
        s = doQuote(id) + wl_row(id) + delim + delim.join(map(doQuote, map(lambda c: showVectorValue(bitvec, c, hl[c], ch), columns)))
        vectors[id] = empty
        print(s, file=out)

        num += 1
        if show_progress and sys.stderr.isatty():
            sys.stderr.write("writing file: {0:.2%} complete\r".format(num / num_total))
            sys.stderr.flush()
    if show_progress and sys.stderr.isatty():
        print("", file=sys.stderr)

### interpret arguments ###

def interpret_header_spec(header_spec, dispatcher):
    ch = ColumnHandler(dispatcher, header_spec["default_aggr"])
    if "levels" in header_spec:
        ch.set_valid_levels(header_spec["levels"])
    for row in header_spec["info"]:
        collector = row[0]
        aggregator = row[1]
        ch.add_info_handler(collector, aggregator)
    return ch

def usage():
    print('usage: {0} [-h|--debug] [-q] [--aggregate <method>] [--num-cutoff <number>] [--age-time <date>] [--from <date>] [--to <date>] [-o <output>] [-s <spec>] [-w <whitelist>] -f <format> -c <config> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-q: be quiet about progress', file=sys.stderr)
    print('--debug: prints debug output', file=sys.stderr)
    print('--num-cutoff <number>: specifies the minimum number of occurrences for a column to appear in the output. default is {0}'.format(str(num_cutoff)), file=sys.stderr)
    print('--age-time <date>: specifies the date to compute the age as "YYYYMMDD". can be omitted', file=sys.stderr)
    print('--from <date>: specifies the start date as "YYYYMMDD". can be omitted', file=sys.stderr)
    print('--to <date>: specifies the end date as "YYYYMMDD". can be omitted', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('-s <spec>: set header specification file', file=sys.stderr)
    print('-w <whitelist>: specifies a patient whitelist. all patients if omitted (warning: slow)', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print('-c <config>: specify config file', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them. "-" represents stdin', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    output = '-'
    settingsFile = None
    settings = {}
    settings['delim'] = ','
    settings['quote'] = '"'
    header_spec = {
        "default_aggr": "binary",
        "info": [
            ["age_bin", "binary"],
            ["dead_field", "binary"],
            ["sex_field", "binary"]
        ]
    }
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
        elif arg == '-q':
            show_progress = False
        elif arg == '-s':
            if not args or args[0] == '--':
                print('-s requires specification file', file=sys.stderr)
                usage()
            with open(args.pop(0), 'r') as input:
                header_spec = json.loads(input.read())
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
            settingsFile = args.pop(0)
            util.read_config(settings, settingsFile, build_dictionary.debugOutput)
        elif arg == '--debug':
            build_dictionary.debugOutput = True
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    if not args:
        print('no input provided', file=sys.stderr)
        usage()

    build_dictionary.reportMissingEntries = False
    build_dictionary.init(settings, settingsFile)

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
    ch = interpret_header_spec(header_spec, dispatch)
    processAll(vectors, header_list, header_counts, allPaths, whitelist, ch)
    with util.OutWrapper(output) as out:
        printResult(vectors, header_list, header_counts, settings['delim'], settings['quote'], whitelist, ch, out)
