# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@";" """
from __future__ import print_function

import collections
import os
import sys
import csv
import json
import re

import util

__doc__ = """
Created on Tue Jan 20 14:10:00 2015

@author: joschi
"""

input_format = {}

TYPE_PRESCRIBED = "prescribed"
TYPE_LABTEST    = "lab-test"
TYPE_DIAGNOSIS  = "diagnosis"
TYPE_PROCEDURE  = "procedure"
TYPE_PROVIDER   = "provider"
TYPE_PHYSICIAN  = "physician"

MODE_OPTIONAL = 0
MODE_DEFAULT = 1
MODE_ARRAY = 2

STATUS_UNKNOWN = 0
STATUS_IN = 1
STATUS_PROF = 2
STATUS_OUT = -1

STATUS_FLAG_MAP = {
    "I": STATUS_IN,
    "O": STATUS_OUT,
    "P": STATUS_PROF
}

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

def handleKey(row, key, mode, hnd):
    if mode == MODE_ARRAY:
        for k in input_format[key]:
            if k in row and row[k] != '':
                hnd(row[k])
        return
    ignore_missing = mode == MODE_DEFAULT
    if key in input_format:
        k = input_format[key]
        if util.is_array(k):
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

    handleKey(row, "diagnosis_icd9", MODE_ARRAY, lambda value: emit(TYPE_DIAGNOSIS, "icd9__" + value))
    handleKey(row, "procedures_icd9", MODE_ARRAY, lambda value: emit(TYPE_PROCEDURE, "icd9__" + value))
    handleKey(row, "procedures_cpt", MODE_ARRAY, lambda value: emit(TYPE_PROCEDURE, "cpt__" + value))
    # TODO HCPCS_CD_1 – HCPCS_CD_45: DESYNPUF: Revenue Center HCFA Common Procedure Coding System
    #handleKey(row, "procedures_hcpcs", MODE_ARRAY, lambda value: emit(TYPE_PROCEDURE, "hcpcs__" + value))
    handleKey(row, "provider_alt", MODE_ARRAY, lambda value: emit(TYPE_PROVIDER, "alt__" + value))
    handleKey(row, "provider_cms", MODE_ARRAY, lambda value: emit(TYPE_PROVIDER, "cms__" + value))
    handleKey(row, "physician_alt", MODE_ARRAY, lambda value: emit(TYPE_PHYSICIAN, "alt__" + value))
    handleKey(row, "physician_cms", MODE_ARRAY, lambda value: emit(TYPE_PHYSICIAN, "cms__" + value))
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

    def handleStatusEvent(date, st):
        if date in statusMap:
            if statusMap[date] != STATUS_IN and st == STATUS_IN:
                statusMap[date] = st
            elif statusMap[date] != STATUS_PROF and st == STATUS_PROF:
                statusMap[date] = st
            elif statusMap[date] == STATUS_UNKNOWN:
                statusMap[date] = st
        else:
            statusMap[date] = st

    def admissionDates(fromDate, toDate):
        if fromDate == '':
            if toDate == '':
                return
            fromDate = toDate
            toDate = ''
        curDate = util.toTime(fromDate)
        endDate = util.toTime(toDate) if toDate != '' else curDate
        while curDate <= endDate:
            handleStatusEvent(curDate, STATUS_IN)
            curDate = util.nextDay(curDate)

    handleKey(row, "admission", MODE_OPTIONAL, lambda in_from:
        handleKey(row, "discharge", MODE_OPTIONAL, lambda in_to:
                admissionDates(in_from, in_to)
            )
        )

    def dates(fromDate, toDate):
        if fromDate == '':
            if toDate == '':
                return
            fromDate = toDate
            toDate = ''
        curDate = util.toTime(fromDate)
        endDate = util.toTime(toDate) if toDate != '' else curDate
        while curDate <= endDate:
            for event in handleEvent(row, claim_id):
                event['time'] = curDate
                handleKey(row, "claim_amount", MODE_OPTIONAL, lambda amount:
                    addCost(event, amount)
                )
                obj['events'].append(event)
            handleStatusEvent(curDate, curStatus)
            handleKey(row, "location_flag", MODE_OPTIONAL, lambda flag:
                handleStatusEvent(curDate, STATUS_FLAG_MAP.get(flag, STATUS_UNKNOWN))
            )
            curDate = util.nextDay(curDate)

    handleKey(row, "claim_from", MODE_OPTIONAL, lambda fromDate:
            handleKey(row, "claim_to", MODE_DEFAULT, lambda toDate:
                dates(fromDate, toDate)
            )
        )

    def emitNDC(date, ndc):
        # TODO add provider/physician here as well?
        event = createEntry(TYPE_PRESCRIBED, "ndc__" + ndc, claim_id)
        curDate = util.toTime(date)
        event['time'] = curDate
        handleKey(row, "location_flag", MODE_OPTIONAL, lambda flag:
            handleStatusEvent(curDate, STATUS_FLAG_MAP.get(flag, STATUS_UNKNOWN))
        )
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
        # TODO add provider/physician here as well?
        event = createEntry(TYPE_LABTEST, "loinc__" + loinc, claim_id, result != '' or resultFlag != '', resultFlag, result)
        event['time'] = util.toTime(date)
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

def process(allPaths, lineFile, classFile, id):
    obj = {
        "info": [],
        "events": [],
        "h_bars": [],
        "v_bars": [ "auto" ],
        "v_spans": [],
        "classes": {}
    }
    util.add_files(obj, lineFile, classFile)

    addInfo(obj, "pid", "Patient", id)
    if len(allPaths) == 0:
        print('warning: no path given', file=sys.stderr)
    statusMap = {}
    for (path, isfile) in allPaths:
        if isfile:
            processFile(path, id, obj, statusMap)
        else:
            util.process_id_directory(path, id, lambda file, id: processFile(file, id, obj, statusMap))
    curInStart = None
    curInEnd = None
    curStatus = STATUS_UNKNOWN
    for k in sorted(statusMap):
        status = statusMap[k]
        if status == curStatus:
            if curInStart is None:
                curInStart = k
            curInEnd = k
        else:
            if curInStart is not None:
                if curStatus == STATUS_IN:
                    obj["v_spans"].append({
                        "from": curInStart,
                        "to": util.nextDay(curInEnd),
                        "class": "in_hospital"
                    })
                elif curStatus == STATUS_PROF:
                    obj["v_spans"].append({
                        "from": curInStart,
                        "to": util.nextDay(curInEnd),
                        "class": "professional"
                    })
                curInStart = None
            curStatus = status
    min_time = float('inf')
    max_time = float('-inf')
    for e in obj["events"]:
        time = e["time"]
        if time < min_time:
            min_time = time
        if time > max_time:
            max_time = time
    obj["start"] = min_time
    obj["end"] = max_time
    addInfo(obj, "event_count", "Events", len(obj["events"]))
    return obj

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

if __name__ == '__main__':
    lineFile = None
    classFile = None
    pid = None
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
            util.read_format(args.pop(0), input_format, usage)
        elif arg == '-o':
            if not args or args[0] == '--':
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
            output = re.sub(r'(^|[^%])((?:%%)*)%p', r'\1\2foo', output).replace('%%', '%')
        elif arg == '-p':
            if not args or args[0] == '--':
                print('no id specified', file=sys.stderr)
                usage()
            pid = args.pop(0)
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
    if pid is None:
        print('need to specify id with -p', file=sys.stderr)
        usage()
    allPaths = []
    util.convert_paths(args, allPaths)
    obj = process(allPaths, lineFile, classFile, pid)
    if output != '-' and not os.path.exists(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))
    with util.OutWrapper(output) as out:
        print(json.dumps(obj, indent=2, sort_keys=True), file=out)
