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
#import simplejson as json
import json
import os.path

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
    pid = "" # find way to determine parent
    if id[0] == '0':
        modCode = id[1:]
    else:
        modCode = id[0:5]+id[6:]
    if modCode in symbols:
        l = symbols[modCode]
        return toEntry(id, pid, l["nonp"], l["nonp"]+" ["+l["desc"]+"] ("+l["prop"]+") "+l["subst"]+" - "+l["pharm"]+" - "+l["pType"])
    return createUnknownEntry(symbols, type, id)

def initPrescribed():
    with open(productFile, 'r') as prFile:
        products = prFile.readlines()
    with open(packageFile, 'r') as paFile:
        packages = paFile.readlines()
    prescribeLookup = {}
    uidLookup = {}
    for i in range(len(products)):
        if i == 0:
            continue
        # PRODUCTID PRODUCTNDC PRODUCTTYPENAME PROPRIETARYNAME PROPRIETARYNAMESUFFIX NONPROPRIETARYNAME DOSAGEFORMNAME ROUTENAME STARTMARKETINGDATE ENDMARKETINGDATE MARKETINGCATEGORYNAME APPLICATIONNUMBER LABELERNAME SUBSTANCENAME ACTIVE_NUMERATOR_STRENGTH ACTIVE_INGRED_UNIT PHARM_CLASSES DEASCHEDULE
        line = products[i].split('\t')
        uid = line[0].strip('\n')
        ptn = line[2].strip('\n')
        prop = line[3].strip('\n')
        nonp = line[5].strip('\n')
        subst = line[13].strip('\n')
        pharm = line[16].strip('\n')
        if uid in uidLookup:
            print("warning duplicate uid: "+uid, file=sys.stderr)
        uidLookup[uid] = {
            "pType": ptn,
            "prop": prop,
            "nonp": nonp,
            "subst": subst,
            "pharm": pharm
        }
    for i in range(len(packages)):
        if i == 0:
            continue
        # PRODUCTID PRODUCTNDC NDCPACKAGECODE PACKAGEDESCRIPTION
        line = packages[i].split('\t')
        uid = line[0].strip('\n')
        #ndc = line[1].strip('\n')
        pc = line[2].strip('\n')
        desc = line[3].strip('\n')
        nid = pc.replace('-', '')
        if uid not in uidLookup:
            print("warning missing uid: "+uid, file=sys.stderr)
            continue
        l = uidLookup[uid]
        if nid in prescribeLookup:
            desc = prescribeLookup[nid]["desc"] + " or " + desc
        prescribeLookup[nid] = {
            "desc": desc,
            "pType": l["pType"],
            "prop": l["prop"],
            "nonp": l["nonp"],
            "subst": l["subst"],
            "pharm": l["pharm"]
        }
    return prescribeLookup

### lab-test ###

def createLabtestEntry(symbols, type, id):
    pid = "" # find parent id
    if id in symbols:
        return toEntry(id, pid, symbols[id], symbols[id])
    return createUnknownEntry(symbols, type, id)

def initLabtest():
    return getGlobalSymbols()

### diagnosis ###

diag_parents = {}
def createDiagnosisEntry(symbols, type, id):
    pid = diag_parents[id] if id in diag_parents else ""
    if id in symbols:
        return toEntry(id, pid, symbols[id], symbols[id])
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
    pid = proc_parents[id] if id in proc_parents else ""
    if id in symbols:
        return toEntry(id, pid, symbols[id], symbols[id])
    return createUnknownEntry(symbols, type, id)

def initProcedure():
    global proc_parents
    codes = getGlobalSymbols()
    codes.update(getICD9())
    proc_parents = readCCS(ccs_proc_file, codes)
    return codes

### unknown ###

def createUnknownEntry(_, type, id, pid=""):
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
        lastCode=""
        for line in file:
            if len(line) < 2:
                continue
            if not line[1].isdigit():
                if line[0] == ' ' and lastCode != "":
                    codes[lastCode] = codes[lastCode] + " " + line.strip()
                continue
            spl = line.split(None, 1)
            lastCode = spl[0]
            codes[lastCode] = spl[1].rstrip()
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
                if line[0] == ' ' and lastCode != "":
                    nums = line.split()
                    for n in nums:
                        parents[n] = cur
                continue
            spl = line.split(None, 1)
            par = spl[0].rtrim('0123456789').rtrim('.')
            cur = "HIERARCHY_" + spl[0]
            parents[cur] = "HIERARCHY_" + par if len(par) > 0 else ""
            codes[cur] = spl[1].rtrim('0123456789 \t\n\r')
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
    with open(file, 'r') as input:
        dict = json.loads(input.read())
    return dict

def enrichDict(file, mid):
    if file == sys.stdout or not os.path.isfile(file):
        dict = {}
    else:
        dict = loadOldDict(file)
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
    if not os.path.isfile(file):
        print("creating config file: "+file, file=sys.stderr)
        with open(file, 'w') as output:
            print(json.dumps(settings, indent=2), file=output)
        return
    config = {}
    with open(file, 'r') as input:
        config = json.loads(input.read())
    for k in config.keys():
        if k not in settings:
            print("unknown setting: "+k, file=sys.stderr)
        else:
            settings[k] = config[k]

def usage():
    print(sys.argv[0]+": -p <file> -c <config> -o <output> [-h|--help]", file=sys.stderr)
    print("-p <file>: specify patient json file", file=sys.stderr)
    print("-c <config>: specify config file. '-' uses default settings", file=sys.stderr)
    print("-o <output>: specify output file. '-' uses standard out", file=sys.stderr)
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
        else:
            print('illegal argument '+val, file=sys.stderr)
            usage()
    return (settings, info)

if __name__ == '__main__':
    (settings, info) = interpretArgs()
    init()
    globalSymbolsFile = settings['filename']
    icd9File = settings['icd9']
    ccs_diag_file = settings['ccs_diag']
    ccs_proc_file = settings['ccs_proc']
    productFile = settings['ndc_prod']
    packageFile = settings['ndc_package']
    enrichDict(info['output'], info['mid'])
