# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@"; """
from __future__ import print_function

import shelve
import sys
import os.path
import json
import hashlib
import random

import util

__doc__ = """
Created on 2015-03-02

@author: joschi
@author: razavian
"""

def writeRow(cols, out, start, length, colZero):
    delim = out['delim'];
    quote = out['quote'];

    def doQuote(cell):
        cell = str(cell)
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    s = doQuote(colZero) + delim;
    if start > 0:
        s += start * delim
    s += delim.join(map(doQuote, cols))
    remain = length - start - len(cols)
    if remain > 0:
        s += remain * delim
    print(s, file=out['out'])

def openDB(pid, data, out, writeHeader):
    db = shelve.open(settings['database'])
    data = db[pid.strip()]
    all_hdrs = [
    ]

    def processHeader(file, db_key):
        hdrs = []
        with open(file, 'r') as hnd:
            hdrs = hnd.read().strip().split(settings['hdr_split'])
        skip = -1
        start = len(all_hdrs)
        for ix, head in enumerate(hdrs):
            if head == settings['join_id']:
                skip = ix
            else:
                all_hdrs.append(db_key + '_' + head)
        return {
            'skip': skip,
            'start': start,
            'data': data[db_key],
            'col_num': len(all_hdrs) - start
        }

    row_definitions = [
        processHeader(settings['header_elig'], 'ELIG'),
        processHeader(settings['header_encs'], 'ENCS'),
        processHeader(settings['header_lab_rsl'], 'LAB_RSL'),
        processHeader(settings['header_med_clms'], 'MED_CLMS'),
        processHeader(settings['header_rx_clms'], 'RX_CLMS'),
    ]
    db.close()
    if writeHeader:
        writeRow(all_hdrs, out, 0, len(all_hdrs), settings['join_id'])
    return (row_definitions, len(all_hdrs), all_hdrs)

def readShelve(pid, settings, output):
    pids = [ pid ]
    if pid == '--all':
        pids = getAll(settings)
    out = {
        'delim': settings['delim'],
        'quote': settings['quote'],
        'out': output
    }
    anonymize = settings['anonymize']['do']
    first = True
    for patientId in pids:
        if anonymize:
            realId = hashlib.sha1(patientId).hexdigest()
            age_shift = 0
            while age_shift == 0:
                age_shift = random.randint(-10, 10)
            date_shift = 0
            while date_shift == 0:
                date_shift = random.randint(-365 * 10, 365 * 10)
        else:
            realId = patientId
        join_id = settings['join_id']
        splitter = settings['row_split']
        (row_defs, length, all_hdrs) = openDB(patientId, settings, out, first)
        first = False
        for row_def in row_defs:
            start = row_def['start']
            col_num = row_def['col_num']
            skip = row_def['skip']
            # manipulation ixs apply before skipping
            age_ixs = [ ix - start for ix in xrange(start, start + col_num) if all_hdrs[ix] in settings['anonymize']['age_columns'] ]
            date_ixs = [ ix - start for ix in xrange(start, start + col_num) if all_hdrs[ix] in settings['anonymize']['date_columns'] ]
            redact_ixs = [ ix - start for ix in xrange(start, start + col_num) if all_hdrs[ix] in settings['anonymize']['redact_columns'] ]
            for row in row_def['data']:
                if row == '':
                    continue
                values = row.strip().split(splitter)
                if anonymize:
                    for ix in age_ixs:
                        values[ix] = str(int(values[ix]) + age_shift)
                    for ix in date_ixs:
                        values[ix] = util.from_time(util.shift_days(util.toTime(values[ix]), date_shift))
                    for ix in redact_ixs:
                        values[ix] = ''
                id = values.pop(skip)
                if len(values) != col_num:
                    print("column mismatch! expected {0} got {1}: {2}".format(str(col_num), str(len(values)), row), file=sys.stderr)
                    continue
                if id != patientId:
                    print("unexpected id! expected {0} got {1}: {2}".format(patientId, id, row))
                    continue
                writeRow(values, out, start, length, realId)

def getAll(settings):
    pids = []
    for file in settings['shelve_id_files']:
        with open(file, 'r') as f:
            for line in f:
                if line == '':
                    continue
                pids.append(line.strip().split()[0])
    return pids

def printList(settings):
    for file in settings['shelve_id_files']:
        with open(file, 'r') as f:
            for line in f:
                if line == '':
                    continue
                print(line.strip().split()[0], file=sys.stdout)

### argument API

def usage():
    print("""
{0}: --all | -p <pid> -c <config> -o <output> [--seed <seed>] [-h|--help] | [-l|--list]
-h|--help: prints this help
--all: print all patients
-p <pid>: specify patient id
-c <config>: specify config file
-o <output>: specify output file. '-' uses standard out
--seed <seed>: specifies the seed for the rng. if omitted the seed is not set. needs to be integer
-l|--list: prints all available patient ids and exits
""".strip().format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)

def interpretArgs():
    settings = {
        'delim': ',',
        'quote': '"',
        'hdr_split': '|',
        'row_split': '|',
        'database': 'db/members.db',
        'header_elig': 'code/headers/elig.hdr',
        'header_encs': 'code/headers/encs.hdr',
        'header_lab_rsl': 'code/headers/lab_rsl.hdr',
        'header_med_clms': 'code/headers/med_clms.hdr',
        'header_rx_clms': 'code/headers/rx_clms.hdr',
        'join_id': 'MEMBER_ID',
        'shelve_id_files': [
            'code/db/set_myeloma.txt',
            'code/db/set_diabetes.txt'
        ],
        'anonymize': {
            'do': False,
            'date_columns': [
                'ELIG_EFFECTIVE_DATE',
                'ELIG_TERMINATION_DATE',
                'ENCS_SERVICE_DATE',
                'ENCS_PAID_DATE',
                'ENCS_ADMIT_DATE',
                'ENCS_DISCHARGE_DATE',
                'LAB_RSL_SERVICE_DATE',
                'MED_CLMS_SERVICE_DATE',
                'MED_CLMS_PAID_DATE',
                'MED_CLMS_ADMIT_DATE',
                'MED_CLMS_DISCHARGE_DATE',
                'RX_CLMS_SERVICE_DATE',
                'RX_CLMS_PAID_DATE',
                'RX_CLMS_PRESCRIPTION_DATE'
            ],
            'age_columns': [
                'ELIG_AGE',
                'LAB_RSL_AGE',
                'RX_CLMS_AGE'
            ],
            'redact_columns': [
                'ELIG_PATIENT_KEY',
                'ELIG_OLD_MEMBER_ID',
                'ELIG_SUBSCRIBER_ID',
                'ELIG_ZIP',
                'ELIG_COUNTRY_CODE',
                'ELIG_PCP_ID',
                'ELIG_GROUP_ID',
                'ELIG_SUB_GROUP_ID',
                'ELIG_PLAN_ID',
                'LAB_RSL_SUBSCRIBER_ID'
            ]
        }
    }
    info = {
        'pid': '',
        'output': '-'
    }
    args = sys.argv[:]
    args.pop(0);
    do_list = False
    while args:
        val = args.pop(0)
        if val == '-h' or val == '--help':
            usage()
        if val == '-l' or val == '--list':
            do_list = True
        elif val == '-p':
            if not args:
                print('-p requires argument', file=sys.stderr)
                usage()
            info['pid'] = args.pop(0)
        elif val == '--all':
            info['pid'] = '--all'
        elif val == '-c':
            if not args:
                print('-c requires argument', file=sys.stderr)
                usage()
            util.read_config(settings, args.pop(0))
        elif val == '-o':
            if not args:
                print('-o requires argument', file=sys.stderr)
                usage()
            info['output'] = args.pop(0)
        elif arg == '--seed':
            if not len(args):
                print('--seed requires integer seed', file=sys.stderr)
                usage()
            try:
                seed = int(args.pop(0))
                random.seed(seed)
            except:
                print('--seed requires integer seed', file=sys.stderr)
                usage()
        else:
            print('illegal argument '+val, file=sys.stderr)
            usage()
    if do_list:
        printList(settings)
        sys.exit(0)
    if info['pid'] == '':
        print('patient id required', file=sys.stderr)
        usage()
    return (settings, info)

if __name__ == '__main__':
    (settings, info) = interpretArgs()
    with util.OutWrapper(info['output']) as output:
        readShelve(info['pid'], settings, output)
