#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 13 11:44:00 2014

@author: joschi
@author: razavian
"""
from __future__ import print_function
import time
import datetime
import shelve
from datetime import datetime,timedelta
import sys
import csv
#import simplejson as json
import json
import os.path

reportMissingEntries = False # only for debugging

def toEntry(id, pid, name, desc):
    return {
        "id": id,
        "parent": pid,
        "name": name,
        "desc": desc
    }

def createEntry(dict, type, id):
    if not id:
        entry = createRootEntry(type)
    else:
        creator = convertLookup.get(type, createUnknownEntry)
        entry = creator(symbolTable.get(type, {}), type, id)
    if type not in dict:
        dict[type] = {}
    dict[type][id] = entry
    pid = entry['parent']
    if pid not in dict[type]:
        createEntry(dict, type, pid)

def init():
    for key in initLookup.keys():
        symbolTable[key] = initLookup[key]()

### prescribed ###

def createPrescribedEntry(symbols, type, id):
    pid = id[:-2] if len(id) == 11 else ""
    if id in symbols:
        l = symbols[id]
        return toEntry(id, pid, l["nonp"], l["nonp"]+" ["+l["desc"]+"] ("+l["prop"]+") "+l["subst"]+" - "+l["pharm"]+" - "+l["pType"])
    return createUnknownEntry(symbols, type, id, pid)

def initPrescribed():
    prescribeLookup = {}
    if not os.path.isfile(productFile):
        return prescribeLookup
    uidLookup = {}
    with open(productFile, 'r') as prFile:
        for row in csv.DictReader(prFile, delimiter='\t', quoting=csv.QUOTE_NONE):
            uid = row['PRODUCTID'].strip()
            fullndc = row['PRODUCTNDC'].strip()
            ndcparts = fullndc.split('-')
            if len(ndcparts) != 2:
                print("invalid NDC (2):" + fullndc + "  " + uid, file=sys.stderr)
                continue
            normndc = ""
            if len(ndcparts[0]) == 4 and len(ndcparts[1]) == 4:
                normndc = "0" + ndcparts[0] + ndcparts[1]
            elif len(ndcparts[0]) == 5 and len(ndcparts[1]) == 3:
                normndc = ndcparts[0] + "0" + ndcparts[1]
            elif len(ndcparts[0]) == 5 and len(ndcparts[1]) == 4:
                normndc = ndcparts[0] + ndcparts[1]
            else:
                print("invalid split NDC (2):" + fullndc + "  " + uid, file=sys.stderr)
                continue
            ndc = ndcparts[0] + ndcparts[1]
            ptn = row['PRODUCTTYPENAME'].strip()
            prop = row['PROPRIETARYNAME'].strip()
            nonp = row['NONPROPRIETARYNAME'].strip()
            subst = row['SUBSTANCENAME'].strip()
            pharm = row['PHARM_CLASSES'].strip()
            if uid in uidLookup:
                print("warning duplicate uid: " + uid, file=sys.stderr)
            uidLookup[uid] = {
                "pType": ptn,
                "prop": prop,
                "nonp": nonp,
                "subst": subst,
                "pharm": pharm
            }
            desc = nonp + " " + ptn
            l = uidLookup[uid]
            if ndc in prescribeLookup or normndc in prescribeLookup:
                continue
            obj = {
                "desc": desc,
                "pType": l["pType"],
                "prop": l["prop"],
                "nonp": l["nonp"],
                "subst": l["subst"],
                "pharm": l["pharm"]
            }
            prescribeLookup[ndc] = obj
            prescribeLookup[normndc] = obj
            prescribeLookup[fullndc] = obj
    if not os.path.isfile(packageFile):
        return prescribeLookup
    with open(packageFile, 'r') as paFile:
        for row in csv.DictReader(paFile, delimiter='\t', quoting=csv.QUOTE_NONE):
            uid = row['PRODUCTID'].strip()
            fullndc = row['NDCPACKAGECODE'].strip()
            ndcparts = fullndc.split('-')
            if len(ndcparts) != 3:
                print("invalid NDC (3):" + fullndc + "  " + uid, file=sys.stderr)
                continue
            normndc = ""
            if len(ndcparts[0]) == 4 and len(ndcparts[1]) == 4 and len(ndcparts[2]) == 2:
                normndc = "0" + ndcparts[0] + ndcparts[1] + ndcparts[2]
            elif len(ndcparts[0]) == 5 and len(ndcparts[1]) == 3 and len(ndcparts[2]) == 2:
                normndc = ndcparts[0] + "0" + ndcparts[1] + ndcparts[2]
            elif len(ndcparts[0]) == 5 and len(ndcparts[1]) == 4 and len(ndcparts[2]) == 1:
                normndc = ndcparts[0] + ndcparts[1] + "0" + ndcparts[2]
            elif len(ndcparts[0]) == 5 and len(ndcparts[1]) == 4 and len(ndcparts[2]) == 2:
                normndc = ndcparts[0] + ndcparts[1] + ndcparts[2]
            else:
                print("invalid split NDC (3):" + fullndc + "  " + uid, file=sys.stderr)
                continue
            ndc = ndcparts[0] + ndcparts[1] + ndcparts[2]
            desc = row['PACKAGEDESCRIPTION'].strip()
            if uid not in uidLookup:
                #print("warning missing uid: " + uid, file=sys.stderr) // not that important since the non-packaged version is already added
                continue
            l = uidLookup[uid]
            if ndc in prescribeLookup:
                desc = prescribeLookup[ndc]["desc"] + " or " + desc
            obj = {
                "desc": desc,
                "pType": l["pType"],
                "prop": l["prop"],
                "nonp": l["nonp"],
                "subst": l["subst"],
                "pharm": l["pharm"]
            }
            prescribeLookup[ndc] = obj
            prescribeLookup[normndc] = obj
            prescribeLookup[fullndc] = obj
    return prescribeLookup

### lab-test ###

def createLabtestEntry(symbols, type, id):
    pid = "" # find parent id
    if id in symbols:
        return toEntry(id, pid, symbols[id], symbols[id])
    return createUnknownEntry(symbols, type, id, pid)

def initLabtest():
    return getGlobalSymbols()

### diagnosis ###

diag_parents = {}
def createDiagnosisEntry(symbols, type, id):
    prox_id = id
    pid = ""
    while len(prox_id) >= 3:
        pid = diag_parents[prox_id] if prox_id in diag_parents else pid
        if prox_id in symbols:
            return toEntry(id, pid, symbols[prox_id], symbols[prox_id])
        prox_id = prox_id[:-1]
    return createUnknownEntry(symbols, type, id, pid)

def initDiagnosis():
    global diag_parents
    codes = getGlobalSymbols()
    codes.update(getICD9())
    diag_parents = readCCS(ccs_diag_file, codes)
    return codes

### procedure ###

proc_parents = {}
def createProcedureEntry(symbols, type, id):
    prox_id = id
    pid = ""
    while len(prox_id) >= 3:
        pid = proc_parents[prox_id] if prox_id in proc_parents else pid
        if prox_id in symbols:
            return toEntry(id, pid, symbols[prox_id], symbols[prox_id])
        prox_id = prox_id[:-1]
    return createUnknownEntry(symbols, type, id, pid)

def initProcedure():
    global proc_parents
    codes = getGlobalSymbols()
    codes.update(getICD9())
    proc_parents = readCCS(ccs_proc_file, codes)
    return codes

### unknown ###

def createUnknownEntry(_, type, id, pid = ""):
    if reportMissingEntries:
        print("unknown entry; type: " + type + " id: " + id, file=sys.stderr)
    return toEntry(id, pid, id, type + " " + id)

### type ###

root_names = {
    "prescribed": "Prescribed Medication",
    "lab-test": "Laboratory Test",
    "diagnosis": "Condition",
    "procedure": "Procedure"
}

root_desc = {
    "prescribed": "Prescribed Medication",
    "lab-test": "Laboratory Test",
    "diagnosis": "Condition",
    "procedure": "Procedure"
}

root_color = {
    "prescribed": "#eb9adb",
    "lab-test": "#80b1d3",
    "diagnosis": "#4daf4a",
    "procedure": "#ff7f00"
}

root_flags = {
    "lab-test": {
        "L": {
            "color": "#fb8072"
        },
        "H": {
            "color": "#fb8072"
        }
    }
}

def createRootEntry(type):
    name = root_names.get(type, type)
    res = toEntry("", "", name, root_desc.get(type, name))
    if type in root_color:
        res["color"] = root_color[type]
    if type in root_flags:
        res["flags"] = root_flags[type]
    return res

### icd9 ###

globalICD9 = {}

def getICD9():
    global globalICD9
    if len(globalICD9.keys()) == 0:
        globalICD9 = initICD9()
    return globalICD9.copy()

def initICD9():
    codes = {}
    if not os.path.isfile(icd9File):
        return codes
    with open(icd9File, 'r') as file:
        lastCode = ""
        for line in file:
            if len(line.strip()) < 2:
                lastCode = ""
                continue
            if not line[1].isdigit():
                if line[0] == ' ' and lastCode != "":
                    noDot = lastCode.replace(".", "")
                    codes[lastCode] = codes[lastCode] + " " + line.strip()
                    codes[noDot] = codes[noDot] + " " + line.strip()
                continue
            spl = line.split(None, 1)
            if len(spl) == 2:
                lastCode = spl[0].strip()
                noDot = lastCode.replace(".", "")
                codes[lastCode] = spl[1].rstrip()
                codes[noDot] = spl[1].rstrip()
            else:
                if line[0] != '(':
                    print("invalid ICD9 line: '" + line.rstrip() + "'", file=sys.stderr)
    return codes

### ccs ###

def readCCS(ccsFile, codes):
    parents = {}
    if not os.path.isfile(ccsFile):
        return codes
    with open(ccsFile, 'r') as file:
        cur = ""
        for line in file:
            if len(line) < 1:
                continue
            if not line[0].isdigit():
                if line[0] == ' ' and cur != "":
                    nums = line.split()
                    for n in nums:
                        parents[n] = cur
                continue
            spl = line.split(None, 1)
            if len(spl) == 2:
                par = spl[0].rstrip('0123456789').rstrip('.')
                cur = "HIERARCHY_" + spl[0]
                parents[cur] = "HIERARCHY_" + par if len(par) > 0 else ""
                codes[cur] = spl[1].rstrip('0123456789 \t\n\r')
            else:
                print("invalid CCS line: '" + line.rstrip() + "'", file=sys.stderr)
    return parents

### general lookup table ###

globalSymbols = {}

def getGlobalSymbols():
    global globalSymbols
    if len(globalSymbols.keys()) == 0:
        globalSymbols = initGlobalSymbols()
    return globalSymbols.copy()

def initGlobalSymbols():
    codes_dict = {}
    if not os.path.isfile(globalSymbolsFile):
        return codes_dict
    with open(globalSymbolsFile, 'r') as file:
        lines = file.readlines()
    for i in range(len(lines)):
        codeList = lines[i].split('#')[0].strip('\n');
        label = lines[i].split('#')[1].strip('\n')
        for code in codeList.split(" "):
            if code != '':
                codes_dict[code] = label
    return codes_dict

### filling dictionary ###

def extractEntries(dict, patient):
    for event in patient['events']:
        createEntry(dict, event['group'], event['id'])

def loadOldDict(file):
    dict = {}
    if file == sys.stdout or not os.path.isfile(file):
        return dict
    with open(file, 'r') as input:
        dict = json.loads(input.read())
    return dict

def enrichDict(file, mid):
    dict = loadOldDict(file)
    if mid == '-':
        patient = json.loads(sys.stdin.read())
    else:
        with open(mid, 'r') as pfile:
            patient = json.loads(pfile.read())
    extractEntries(dict, patient)
    if file == sys.stdout:
        print(json.dumps(dict, indent=2), file=file)
    else:
        with open(file, 'w') as output:
            print(json.dumps(dict, indent=2), file=output)

### argument API

icd9File = 'code/icd9/ucod.txt'
ccs_diag_file = 'code/ccs/multi_diag.txt'
ccs_proc_file = 'code/ccs/multi_proc.txt'
productFile = 'code/ndc/product.txt'
packageFile = 'code/ndc/package.txt'
globalSymbolsFile = 'code/icd9/code_names.txt'
globalMid = '2507387001'

convertLookup = {
    "prescribed": createPrescribedEntry,
    "lab-test": createLabtestEntry,
    "diagnosis": createDiagnosisEntry,
    "procedure": createProcedureEntry
}

initLookup = {
    "prescribed": initPrescribed,
    "lab-test": initLabtest,
    "diagnosis": initDiagnosis,
    "procedure": initProcedure
}

symbolTable = {}

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
    print("{0}: -p <file> -c <config> -o <output> [-h|--help] [--lookup <id...>]".format(sys.argv[0]), file=sys.stderr)
    print("-p <file>: specify patient json file. '-' uses standard in", file=sys.stderr)
    print("-c <config>: specify config file. '-' uses default settings", file=sys.stderr)
    print("-o <output>: specify output file. '-' uses standard out", file=sys.stderr)
    print("--lookup <id...>: lookup mode. translates ids in shorthand notation '${group_id}__${type_id}'. '-' uses standard in with ids separated by spaces", file=sys.stderr)
    print("-h|--help: prints this help.", file=sys.stderr)
    sys.exit(1)

def interpretArgs():
    settings = {
        'filename': globalSymbolsFile,
        'ndc_prod': productFile,
        'ndc_package': packageFile,
        'icd9': icd9File,
        'ccs_diag': ccs_diag_file,
        'ccs_proc': ccs_proc_file
    }
    info = {
        'mid': globalMid,
        'output': sys.stdout
    }
    lookupMode = False
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
            info['mid'] = args.pop(0)
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
        elif val == '--lookup':
            lookupMode = True
            break
        else:
            print('illegal argument '+val, file=sys.stderr)
            usage()
    return (settings, info, lookupMode, args)

if __name__ == '__main__':
    (settings, info, lookupMode, rest) = interpretArgs()
    globalSymbolsFile = settings['filename']
    icd9File = settings['icd9']
    ccs_diag_file = settings['ccs_diag']
    ccs_proc_file = settings['ccs_proc']
    productFile = settings['ndc_prod']
    packageFile = settings['ndc_package']
    init()
    if lookupMode:
        dict = {}

        def addEntry(e):
            spl = e.split('__', 1)
            if len(spl) != 2:
                print("shorthand format is '${group_id}__${type_id}': " + e, file=sys.stderr)
                sys.exit(1)
            createEntry(dict, spl[0].strip(), spl[1].strip())

        for e in rest:
            if e == "-":
                for eid in sys.stdin.read().split(" "):
                    if len(eid) > 0 and eid != "id":
                        addEntry(eid)
            else:
                addEntry(e)

        file = info['output']
        if file == sys.stdout:
            print(json.dumps(dict, indent=2), file=file)
        else:
            with open(file, 'w') as output:
                print(json.dumps(dict, indent=2), file=output)
    else:
        enrichDict(info['output'], info['mid'])
