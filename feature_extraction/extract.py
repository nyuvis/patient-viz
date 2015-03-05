#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 2015-03-04

@author: joschi
"""
from __future__ import print_function
import shelve
import sys
import os.path
import csv
#import simplejson as json
import json
import BitVector

sys.path.append('..')

import build_dictionary
import opd_get_patient

def handleRow(row, id, cb):
    obj = {
        "info": [],
        "events": [],
        "h_bars": [],
        "v_bars": [ "auto" ]
    }
    opd_get_patient.handleRow(row, obj)
    dict = {}
    build_dictionary.extractEntries(dict, obj)
    for group in dict.keys():
        for type in dict[group]:
            cb(id, group, type["id"])

def processFile(inputFile, id_column, cb):
    if inputFile == '-':
        for row in csv.DictReader(sys.stdin):
            handleRow(row, row[id_column], cb)
        return
    with open(inputFile) as csvFile:
        for row in csv.DictReader(csvFile):
            handleRow(row, row[id_column], cb)

def processDirectory(dir, id_column, cb):
    for (_, _, files) in os.walk(dir):
        for file in files:
            if file.endswith(".csv"):
                processFile(dir + '/' + file, id_column, cb)

def getBitVector(vectors, header_list, id):
    if id in vectors:
        bitvec = vectors[id]
    else:
        bitvec = BitVector.BitVector(size=0)
    if len(bitvec) < len(header_list):
        diff = len(header_list) - len(bitvec)
        bitvec = bitvec + BitVector.BitVector(size=diff)
    vectors[id] = bitvec
    return bitvec

def getHead(group, type):
    if "__" in group:
        print("group name is using __: {0}".format(group), file=sys.stderr)
    return group + "__" + type

def processAll(vectors, header_list, path_tuples):
    header = {}

    def handle(id, group, type):
        head = getHead(group, type)
        if head not in header:
            header[head] = len(header_list)
            header_list.append(head)
        bitvec = getBitVector(vectors, header_list, id)
        bitvec[header[head]] = True

    id_column = opd_get_patient.input_format["patient_id"]
    for (path, isfile) in path_tuples:
        if isfile:
            processFile(path, id_column, handle)
        else:
            processDirectory(path, id_column, handle)


def printResult(vectors, header_list, delim, quote, out):

    def doQuote(cell):
        if cell.find(delim) < 0 and cell.find(quote) < 0:
            return cell
        return  quote + cell.replace(quote, quote + quote) + quote

    str = doQuote("id") + delim + delim.join(map(doQuote, header_list))
    print(str, file=out)

    for id in vectors.keys():
        bitvec = vectors[id]
        str = doQuote(id) + delim + delim.join(map(doQuote, map(lambda v: 1 if v else 0, bitvec)))
        print(str, file=out)

def usage():
    print('usage: {0} [-h] [-o <output>] -f <format> -c <config> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print('-c <config>: specify config file. "-" uses default settings', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them. "-" represents stdin', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    output = '-'
    settings = {
        'delim': ',',
        'quote': '"',
        'filename': build_dictionary.globalSymbolsFile,
        'ndc_prod': build_dictionary.productFile,
        'ndc_package': build_dictionary.packageFile,
        'icd9': build_dictionary.icd9File,
        'ccs_diag': build_dictionary.ccs_diag_file,
        'ccs_proc': build_dictionary.ccs_proc_file
    }
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '--':
            break
        if arg == '-h':
            usage()
        if arg == '-f' or args[0] == '--':
            if not args:
                print('-f requires format file', file=sys.stderr)
                usage()
            opd_get_patient.read_format(args.pop(0))
        elif arg == '-o':
            if not args or args[0] == '--':
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
        elif arg == '-c':
            if not args or args[0] == '--':
                print('-c requires argument', file=sys.stderr)
                usage()
            build_dictionary.readConfig(settings, args.pop(0))
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    build_dictionary.globalSymbolsFile = settings['filename']
    build_dictionary.icd9File = settings['icd9']
    build_dictionary.ccs_diag_file = settings['ccs_diag']
    build_dictionary.ccs_proc_file = settings['ccs_proc']
    build_dictionary.productFile = settings['ndc_prod']
    build_dictionary.packageFile = settings['ndc_package']
    build_dictionary.init()

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
    processAll(vectors, header_list, allPaths)
    if output == '-':
        printResult(vectors, header_list, settings['delim'], settings['quote'], sys.stdout)
    else:
        with open(output, 'w') as file:
            printResult(vectors, header_list, settings['delim'], settings['quote'], file)
