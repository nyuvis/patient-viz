# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/../call.sh" "$0" "$@";" """
from __future__ import print_function

import sys
import os.path
import csv
import json
import random
import re

sys.path.append('..')

import util
import build_dictionary

__doc__ = """
Created on 2015-06-02

@author: joschi
"""

def do_process(out, input_csv, input_header, limit, delim, quote):

    def doQuote(cell):
        cell = str(cell)
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    def do_header(hd):
        lookup = {}
        if input_header is not None:
            with open(input_header, 'r') as header_file:
                lookup = json.loads(header_file.read())

        def get_name(h):
            spl = h.split('__', 1)
            group = spl[0]
            type = spl[1] if len(spl) >= 2 else ""
            if group not in lookup:
                return h
            g = lookup[group]
            if type not in g:
                return h
            while True:
                cand = g[type]
                if 'alias' in cand and cand['alias'] in g:
                    type = g
                else:
                    break
            return re.sub('\s+', ' ', '{0} ({1} - {2})'.format(cand['name'], group, cand['id']))

        print(delim.join(map(doQuote, map(get_name, hd))), file=out)

    def do_read(file):
        header = True
        reservoir = []
        for (ix, row) in enumerate(csv.reader(file, delimiter=str(delim), quotechar=str(quote))):
            if header:
                do_header(row)
                header = False
                continue
            if limit is None:
                print(delim.join(map(doQuote, row)), file=out)
                continue
            if len(reservoir) < limit:
                reservoir.append(row)
                continue
            pos = random.randint(0, ix)
            if pos < len(reservoir):
                reservoir[pos] = row
        for row in reservoir:
            print(delim.join(map(doQuote, row)), file=out)

    if input_csv == '-':
        do_read(sys.stdin)
    else:
        with open(input_csv, 'r') as csvfile:
            do_read(csvfile)

def usage():
    print('usage: {0} [-h] [-c <file>] [-i <input>] [-n <file>] [-l <limit>] [-o <output>] [--seed <seed>]'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-c <config>: specify config file', file=sys.stderr)
    print('-i <output>: specifies input file. stdin if omitted or "-"', file=sys.stderr)
    print('-n <file>: specifies the name file. no name mapping if omitted', file=sys.stderr)
    print('-l <limit>: specifies the output limit. no limit if omitted', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('--seed <seed>: specifies the seed for the rng. if omitted the seed is not set', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    output = '-'
    settingsFile = None
    settings = {}
    settings['delim'] = ','
    settings['quote'] = '"'
    seed = None
    limit = None
    input_csv = '-'
    input_header = None
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
        elif arg == '-c':
            if not len(args):
                print('-c requires argument', file=sys.stderr)
                usage()
            settingsFile = args.pop(0)
            util.read_config(settings, settingsFile, build_dictionary.debugOutput)
        elif arg == '-i':
            if not len(args):
                print('-i requires argument', file=sys.stderr)
                usage()
            input_csv = args.pop(0)
        elif arg == '-n':
            if not len(args):
                print('-n requires argument', file=sys.stderr)
                usage()
            input_header = args.pop(0)
        elif arg == '-l':
            if not len(args):
                print('-l requires argument', file=sys.stderr)
                usage()
            limit = int(args.pop(0))
        elif arg == '--seed':
            if not len(args):
                print('--seed requires seed', file=sys.stderr)
                usage()
            seed = args.pop(0)
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    random.seed(seed)

    with util.OutWrapper(output) as out:
        do_process(out, input_csv, input_header, limit, settings['delim'], settings['quote'])
