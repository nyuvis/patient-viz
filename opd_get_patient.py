#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 20 14:10:00 2015

@author: joschi
"""
from __future__ import print_function
import time as time_lib
from datetime import datetime, timedelta
import os
import sys
import csv
#import simplejson as json
import json

idField = 'DESYNPUF_ID'

TYPE_PRESCRIBED = "prescribed"
TYPE_LABTEST    = "lab-test"
TYPE_DIAGNOSIS  = "diagnosis"
TYPE_PROCEDURE  = "procedure"

gender_label = {
    1: "primary",
    2: "danger"
}
gender_map = {
    1: "M",
    2: "W"
}

def toTime(s):
    return int(time_lib.mktime(datetime.strptime(s, "%Y%m%d").timetuple()))

def nextDay(stamp):
    return int(time_lib.mktime((datetime.fromtimestamp(stamp) + timedelta(days = 1)).timetuple()))

def addInfo(obj, id, key, value, hasLabel = False, label = ""):
    for info in obj["info"]:
        if info["id"] == id:
            print('duplicate "'+id+'" new: '+str(value)+' old: '+str(info["value"]), file=sys.stderr)
            return
    node = {
        "id": id,
        "name": key,
        "value": value,
    }
    if hasLabel:
        node["label"] = label
    obj["info"].append(node)

def handleKey(row, key, hnd):
    if key in row:
        hnd(row[key])

def createEntry(group, id, hasResult = False, resultFlag = False, result = ""):
    res = {
        "id": id,
        "group": group
    }
    if hasResult:
        res["flag_value"] = result
        res["flag"] = resultFlag
    return res

def handleEvent(row):
    res = []
    def emit(type, value):
        if value != '':
            res.append(createEntry(type, value))

    dgns_cols = ['ICD9_DGNS_CD_' + str(n) for n in xrange(1, 11)]
    for icd9 in dgns_cols:
        handleKey(row, icd9, lambda value: emit(TYPE_DIAGNOSIS, value))
    prcdr_cols = ['ICD9_PRCDR_CD_' + str(n) for n in xrange(1, 7)]
    for icd9 in prcdr_cols:
        handleKey(row, icd9, lambda value: emit(TYPE_PROCEDURE, value))
    # TODO HCPCS_CD_1 – HCPCS_CD_45: DESYNPUF: Revenue Center HCFA Common Procedure Coding System
    return res

def handleRow(row, obj):
    handleKey(row, 'BENE_BIRTH_DT', lambda value:
            addInfo(obj, 'age', 'Age', 2012 - int(str(value)[0:4])) # FIXME come up with something better later -- maybe no age but birth year?
        )
    handleKey(row, 'BENE_SEX_IDENT_CD', lambda value:
            addInfo(obj, 'gender', 'Gender', gender_map.get(value, 'U'), True, gender_label.get(value, "default"))
        )

    def dates(fromDate, toDate):
        if fromDate == '':
            if toDate == '':
                return
            fromDate = toDate
            toDate = ''
        curDate = toTime(fromDate)
        if toDate != '':
            # time span
            endDate = toTime(toDate)
            while curDate <= endDate:
                for event in handleEvent(row):
                    event['time'] = curDate
                    obj['events'].append(event)
                curDate = nextDay(curDate)
        else:
            # single event
            for event in handleEvent(row):
                event['time'] = curDate
                obj['events'].append(event)

    handleKey(row, 'CLM_FROM_DT', lambda fromDate:
            handleKey(row, 'CLM_THRU_DT', lambda toDate:
                dates(fromDate, toDate)
            )
        )

def processFile(inputFile, id, obj):
    with open(inputFile) as csvFile:
        reader = csv.DictReader(csvFile)
        for row in reader:
            if id == row[idField]:
                handleRow(row, obj)

def processDirectory(dir, id, obj):
    for (_, _, files) in os.walk(dir):
        for file in files:
            if file.endswith(".csv"):
                processFile(dir + '/' + file, id, obj)

def usage():
    print('usage: {} [-h] [-o <output>] -p <id> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('-p <id>: specifies the patient id', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    id = None
    output = '-'
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '--':
            break
        if arg == '-h':
            usage()
        if arg == '-o':
            if not args:
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
            if output == '--':
                print('-o requires output file', file=sys.stderr)
                usage()
        elif arg == '-p':
            if not args:
                print('no id specified', file=sys.stderr)
                usage()
            id = args.pop(0)
            if id == '--':
                print('no id specified', file=sys.stderr)
                usage()
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()
    if id is None:
        print('need to specify id with -p', file=sys.stderr)
        usage()
    allPaths = []
    while args:
        path = args.pop(0)
        if os.path.isfile(path):
            allPaths.append((path, True))
        elif os.path.isdir(path):
            allPaths.append((path, False))
        else:
            print('illegal argument: '+path+' is neither file nor directory', file=sys.stderr)
    obj = {
        "info": [],
        "events": [],
        "h_bars": [],
        "v_bars": [ "auto" ]
    }
    addInfo(obj, "pid", "Patient", id)
    if len(allPaths) == 0:
        print('warning: no path given', file=sys.stderr)
    for (path, isfile) in allPaths:
        if isfile:
            processFile(path, id, obj)
        else:
            processDirectory(path, id, obj)
    min_time = sys.maxint
    max_time = -sys.maxint-1
    for e in obj["events"]:
        time = e["time"]
        if time < min_time:
            min_time = time
        if time > max_time:
            max_time = time
    obj["start"] = min_time
    obj["end"] = max_time
    addInfo(obj, "event_count", "Events", len(obj["events"]))
    file = sys.stdout if output == '-' else output
    if file == sys.stdout:
        print(json.dumps(obj, indent=2), file=file)
    else:
        with open(file, 'w') as ofile:
            print(json.dumps(obj, indent=2), file=ofile)
        ofile.close()
