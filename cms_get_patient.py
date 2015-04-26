#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 20 14:10:00 2015

@author: joschi
"""
from __future__ import print_function
import time as time_lib
from datetime import datetime, timedelta
import collections
import os
import sys
import csv
#import simplejson as json
import json

import util

input_format = {}

TYPE_PRESCRIBED = "prescribed"
TYPE_LABTEST    = "lab-test"
TYPE_DIAGNOSIS  = "diagnosis"
TYPE_PROCEDURE  = "procedure"

MODE_OPTIONAL = 0
MODE_DEFAULT = 1
MODE_ARRAY = 2

STATUS_UNKNOWN = 0
STATUS_IN = 1
STATUS_OUT = -1

gender_label = {
    "1": "primary",
    "2": "danger",
    "M": "primary",
    "W": "danger"
}
gender_map = {
    "1": "M",
    "2": "W",
    "M": "M",
    "W": "W"
}

def toTime(s):
    return int(time_lib.mktime(datetime.strptime(s, "%Y%m%d").timetuple()))

def nextDay(stamp):
    return int(time_lib.mktime((datetime.fromtimestamp(stamp) + timedelta(days = 1)).timetuple()))

def addInfo(obj, id, key, value, hasLabel = False, label = ""):
    for info in obj["info"]:
        if info["id"] == id:
            if str(value) != str(info["value"]):
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

def is_array(v):
    return not isinstance(v, (str, unicode)) and isinstance(v, collections.Sequence)

def handleKey(row, key, mode, hnd):
    if mode == MODE_ARRAY:
        for k in input_format[key]:
            if k in row and row[k] != '':
                hnd(row[k])
        return
    ignore_missing = mode == MODE_DEFAULT
    if key in input_format:
        k = input_format[key]
        if is_array(k):
            found = False
            for key in k:
                if key in row and row[key] != '':
                    hnd(row[key])
                    found = True
                    break
            if not found and ignore_missing:
                hnd('')
        else:
            if k in row and row[k] != '':
                hnd(row[k])
            elif ignore_missing:
                hnd('')
    elif ignore_missing:
        hnd('')

def createEntry(group, id, claim_id, hasResult = False, resultFlag = False, result = ""):
    res = {
        "id": id,
        "group": group
    }
    if claim_id[0] is not None:
        res["row_id"] = claim_id[0]
    if hasResult:
        res["flag_value"] = result
        res["flag"] = resultFlag
    return res

def handleEvent(row, claim_id):
    res = []
    def emit(type, value):
        if value != '':
            res.append(createEntry(type, value, claim_id))

    # TODO HCPCS_CD_1 – HCPCS_CD_45: DESYNPUF: Revenue Center HCFA Common Procedure Coding System
    handleKey(row, "diagnosis", MODE_ARRAY, lambda value: emit(TYPE_DIAGNOSIS, value))
    handleKey(row, "procedures", MODE_ARRAY, lambda value: emit(TYPE_PROCEDURE, value))
    return res

def handleRow(row, obj, statusMap={}, status=STATUS_UNKNOWN):
    curStatus = status
    claim_id = [ None ]

    def setClaimId(cid):
        claim_id[0] = cid

    handleKey(row, "claim_id", MODE_OPTIONAL, lambda value:
            setClaimId(value)
        )

    handleKey(row, "age", MODE_OPTIONAL, lambda value:
            addInfo(obj, 'age', 'Age', value)
        )
    handleKey(row, "born", MODE_OPTIONAL, lambda value:
            addInfo(obj, 'born', 'Born', int(str(value)[0:4]) if len(str(value)) >= 4 else 'N/A')
        )
    handleKey(row, "death", MODE_DEFAULT, lambda value:
            addInfo(obj, 'death', 'Died', int(str(value)[0:4]) if len(str(value)) >= 4 else 'N/A')
        )
    handleKey(row, "gender", MODE_OPTIONAL, lambda value:
            addInfo(obj, 'gender', 'Gender', gender_map.get(str(value), 'U'), True, gender_label.get(str(value), "default"))
        )

    def addCost(event, amount):
        event['cost'] = amount

    def handleStatusEvent(date):
        if date in statusMap:
            if statusMap[date] != STATUS_IN and curStatus == STATUS_IN:
                statusMap[date] = curStatus
            elif statusMap[date] == STATUS_UNKNOWN:
                statusMap[date] = curStatus
        elif curStatus != STATUS_UNKNOWN:
            statusMap[date] = curStatus

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
                for event in handleEvent(row, claim_id):
                    event['time'] = curDate
                    handleKey(row, "claim_amount", MODE_OPTIONAL, lambda amount:
                        addCost(event, amount)
                    )
                    obj['events'].append(event)
                handleStatusEvent(curDate)
                curDate = nextDay(curDate)
        else:
            # single event
            for event in handleEvent(row, claim_id):
                event['time'] = curDate
                obj['events'].append(event)
            handleStatusEvent(curDate)

    handleKey(row, "claim_from", MODE_OPTIONAL, lambda fromDate:
            handleKey(row, "claim_to", MODE_DEFAULT, lambda toDate:
                dates(fromDate, toDate)
            )
        )

    def emitNDC(date, ndc):
        event = createEntry(TYPE_PRESCRIBED, ndc, claim_id)
        event['time'] = toTime(date)
        handleKey(row, "prescribed_amount", MODE_OPTIONAL, lambda amount:
            addCost(event, amount)
        )
        obj['events'].append(event)

    handleKey(row, "prescribed_date", MODE_OPTIONAL, lambda date:
            handleKey(row, "prescribed", MODE_OPTIONAL, lambda ndc:
                emitNDC(date, ndc)
            )
        )

    def emitLab(date, loinc, result, resultFlag):
        event = createEntry(TYPE_LABTEST, loinc, claim_id, result != '' or resultFlag != '', resultFlag, result)
        event['time'] = toTime(date)
        obj['events'].append(event)

    handleKey(row, "lab_date", MODE_OPTIONAL, lambda date:
            handleKey(row, "lab_code", MODE_OPTIONAL, lambda loinc:
                handleKey(row, "lab_result", MODE_DEFAULT, lambda result:
                    handleKey(row, "lab_flag", MODE_DEFAULT, lambda flag:
                        emitLab(date, loinc, result, flag)
                    )
                )
            )
        )

def processFile(inputFile, id, obj, statusMap):
    if inputFile == '-':
        for row in csv.DictReader(sys.stdin):
            if id == row[input_format["patient_id"]]:
                handleRow(row, obj, statusMap, STATUS_UNKNOWN)
        return
    with open(inputFile) as csvFile:
        for row in csv.DictReader(csvFile):
            if id == row[input_format["patient_id"]]:
                status = STATUS_UNKNOWN
                if "inpatient" in inputFile.lower():
                    status = STATUS_IN
                elif "outpatient" in inputFile.lower():
                    status = STATUS_OUT
                handleRow(row, obj, statusMap, status)

def processDirectory(dir, id, obj, statusMap):
    for (root, _, files) in os.walk(dir):
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
        for file in files:
            if file.endswith(".csv"):
                processFile(os.path.join(root, file), id, obj, statusMap)

def processLine(obj, line):
    sp = line.strip().split(':', 2)
    if len(sp) < 2:
        print('invalid line in line file: '+line, file=sys.stderr)
        return
    lid = sp[0]
    if lid != id and len(lid):
        return
    if "__" in sp[1]:
        sps = sp[1].split('__', 1)
        obj["h_bars"].append({
            "group": sps[0],
            "id": sps[1]
        })
    else:
        sps = sp[1].split('-', 1)
        o = {
            "from": toTime(sps[0])
        }
        if len(sps) > 1:
            o["to"] = toTime(sps[1])
        if len(sp) > 2:
            o["class"] = sp[2]
        obj["v_spans"].append(o)

def usage():
    print('usage: {0} [-h] [-o <output>] -f <format> -p <id> [-l <file>] [-c <file>] -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print('-p <id>: specifies the patient id', file=sys.stderr)
    print('-l <file>: specifies a file for line and span infos', file=sys.stderr)
    print('-c <file>: specifies a file for class definitions as json object', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them. "-" represents stdin', file=sys.stderr)
    exit(1)

def read_format(file):
    global input_format
    if not os.path.isfile(file):
        print('invalid format file: {0}'.format(file), file=sys.stderr)
        usage()
    with open(file) as formatFile:
        input_format = json.loads(formatFile.read())

if __name__ == '__main__':
    lineFile = None
    classFile = None
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
        if arg == '-f':
            if not args or args[0] == '--':
                print('-f requires format file', file=sys.stderr)
                usage()
            read_format(args.pop(0))
        elif arg == '-o':
            if not args or args[0] == '--':
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
        elif arg == '-p':
            if not args or args[0] == '--':
                print('no id specified', file=sys.stderr)
                usage()
            id = args.pop(0)
        elif arg == '-l':
            if not args or args[0] == '--':
                print('no file specified', file=sys.stderr)
                usage()
            lineFile = args.pop(0)
        elif arg == '-c':
            if not args or args[0] == '--':
                print('no file specified', file=sys.stderr)
                usage()
            classFile = args.pop(0)
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()
    if id is None:
        print('need to specify id with -p', file=sys.stderr)
        usage()
    allPaths = []
    while args:
        path = args.pop(0)
        if os.path.isfile(path) or path == '-':
            allPaths.append((path, True))
        elif os.path.isdir(path):
            allPaths.append((path, False))
        else:
            print('illegal argument: '+path+' is neither file nor directory', file=sys.stderr)
    obj = {
        "info": [],
        "events": [],
        "h_bars": [],
        "v_bars": [ "auto" ],
        "v_spans": [],
        "classes": {}
    }
    if lineFile is not None:
        with open(lineFile, 'r') as lf:
            for line in lf:
                processLine(obj, line)
    if classFile is not None:
        with open(classFile, 'r') as cf:
            obj["classes"] = json.loads(cf.read())

    addInfo(obj, "pid", "Patient", id)
    if len(allPaths) == 0:
        print('warning: no path given', file=sys.stderr)
    statusMap = {}
    for (path, isfile) in allPaths:
        if isfile:
            processFile(path, id, obj, statusMap)
        else:
            processDirectory(path, id, obj, statusMap)
    curInStart = None
    curInEnd = None
    for k in sorted(statusMap):
        status = statusMap[k]
        if status == STATUS_IN:
            if curInStart is None:
                curInStart = k
            curInEnd = k
        elif status == STATUS_OUT:
            if curInStart is not None:
                obj["v_spans"].append({
                    "from": curInStart,
                    "to": nextDay(curInEnd),
                    "class": "in_hospital"
                })
                curInStart = None
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
    if output != '-' and not os.path.exists(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))
    with util.OutWrapper(output) as out:
        print(json.dumps(obj, indent=2), file=out)
