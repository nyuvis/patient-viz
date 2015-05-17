#!/bin/bash
# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@"; """
from __future__ import print_function

import shelve
import sys
import os.path
import json

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
    return (row_definitions, len(all_hdrs))

def readShelve(pid, settings, output):
    pids = [ pid ]
    if pid == '--all':
        pids = getAll(settings)
    out = {
        'delim': settings['delim'],
        'quote': settings['quote'],
        'out': output
    }
    first = True
    for patientId in pids:
        join_id = settings['join_id']
        splitter = settings['row_split']
        (row_defs, length) = openDB(patientId, settings, out, first)
        first = False
        for row_def in row_defs:
            start = row_def['start']
            skip = row_def['skip']
            for row in row_def['data']:
                if row == '':
                    continue
                values = row.strip().split(splitter)
                id = values.pop(skip)
                if len(values) != row_def['col_num']:
                    print("column mismatch! expected {0} got {1}: {2}".format(str(row_def['col_num']), str(len(values)), row), file=sys.stderr)
                    continue
                writeRow(values, out, start, length, id)

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
                print(line.strip(), file=sys.stdout)

### argument API

def usage():
    print("{0}: --all | -p <pid> -c <config> -o <output> [-h|--help] | [-l|--list]".format(sys.argv[0]), file=sys.stderr)
    print("--all: print all patients", file=sys.stderr)
    print("-p <pid>: specify patient id", file=sys.stderr)
    print("-c <config>: specify config file", file=sys.stderr)
    print("-o <output>: specify output file. '-' uses standard out", file=sys.stderr)
    print("-h|--help: prints this help", file=sys.stderr)
    print("-l|--list: prints all available patient ids and exits", file=sys.stderr)
    sys.exit(1)

def interpretArgs():
    settings = {
        'delim': ',',
        'quote': '"',
        'hdr_split': '|',
        'row_split': '|',
        'database': '/m/data/data_April24_2014.db',
        'header_elig': '/m/data/headers/elig.hdr',
        'header_encs': '/m/data/headers/encs.hdr',
        'header_lab_rsl': '/m/data/headers/lab_rsl.hdr',
        'header_med_clms': '/m/data/headers/med_clms.hdr',
        'header_rx_clms': '/m/data/headers/rx_clms.hdr',
        'join_id': 'MEMBER_ID',
        'shelve_id_files': [
            '/m/data/memberIds/mMyeloma.txt',
            '/m/data/memberIds/mdiabetes.txt'
        ]
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
