#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 2015-03-02

@author: joschi
@author: razavian
"""
from __future__ import print_function
import shelve
import sys
import os.path
#import simplejson as json
import json

def writeRow(cols, out, start, length, colZero):
    delim = out['delim'];
    quote = out['quote'];

    def doQuote(cell):
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    str = doQuote(colZero) + delim;
    if start > 0:
        str += start * delim
    str += map(doQuote, cols).join(delim)
    remain = length - start - len(cols)
    if remain > 0:
        str += remain * delim
    print(str, file=out['out'])

def openDB(pid, data, out):
    db = shelve.open(settings['database'])
    data = db[pid.strip()]
    all_hdrs = [
    ]

    def processHeader(file, db_key):
        hdrs = []
        with open(file, 'r') as hnd:
            hdrs = hnd.read().split(settings['hdr_split'])
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
    writeRow(all_hdrs, out, 0, len(all_hdrs), settings['join_id'])
    return (row_definitions, len(all_hdrs))

def readShelve(pid, settings, output):
    out = {
        'delim': settings['delim'],
        'quote': settings['quote'],
        'out': output
    }
    join_id = settings['join_id']
    splitter = settings['row_split']
    (row_defs, length) = openDB(pid, settings, out)
    for row_def in row_defs:
        start = row_def['start']
        skip = row_def['skip']
        for row in row_def['data']:
            if row == '':
                continue
            values = row.split(splitter)
            if len(values) != row_def['col_num']:
                print("column mismatch! expected {} got {}: {}".format(row_def['col_num'], len(values), row), file=sys.stderr)
                continue
            id = row.pop(skip)
            writeRow(row, out, start, length, id)

### argument API

def readConfig(settings, file):
    if file == '-':
        return
    config = {}
    if os.path.isfile(file):
        with open(file, 'r') as input:
            config = json.loads(input.read())
    settings.update(config)
    if set(settings.keys()) - set(config.keys()):
        with open(file, 'w') as output:
            print(json.dumps(settings, indent=2), file=output)

def usage():
    print(sys.argv[0]+": -p <pid> -c <config> -o <output> [-h|--help]", file=sys.stderr)
    print("-p <pid>: specify patient id", file=sys.stderr)
    print("-c <config>: specify config file. '-' uses default settings", file=sys.stderr)
    print("-o <output>: specify output file. '-' uses standard out", file=sys.stderr)
    print("-h|--help: prints this help", file=sys.stderr)
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
        'join_id': 'MEMBER_ID'
    }
    info = {
        'pid': '',
        'output': sys.stdout
    }
    args = sys.argv[:]
    args.pop(0);
    while args:
        val = args.pop(0)
        if val == '-h' or val == '--help':
            usage()
        elif val == '-p':
            if not args:
                print('-p requires argument', file=sys.stderr)
                usage()
            info['pid'] = args.pop(0)
        elif val == '-c':
            if not args:
                print('-c requires argument', file=sys.stderr)
                usage()
            readConfig(settings, args.pop(0))
        elif val == '-o':
            if not args:
                print('-o requires argument', file=sys.stderr)
                usage()
            info['output'] = args.pop(0)
            if info['output'] == '-':
                info['output'] = sys.stdout
        else:
            print('illegal argument '+val, file=sys.stderr)
            usage()
    if info['pid'] == '':
        print('patient id required', file=sys.stderr)
        usage()
    return (settings, info)

if __name__ == '__main__':
    (settings, info) = interpretArgs()
    if info['output'] == '-':
        readShelve(info['pid'], settings, sys.stdout)
    else:
        with open(info['output'], 'w') as output:
            readShelve(info['pid'], settings, output)
