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
    prFile.close()
    with open(packageFile, 'r') as paFile:
        packages = paFile.readlines()
    paFile.close()
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

def createDiagnosisEntry(symbols, type, id):
    if len(id) > 0 and (id[0] == 'V' or id[0] == 'E'):
        if len(id) > 4:
            pid = id[:4]
        elif(len(id) > 1):
            pid = id[0]
        else:
            pid = ""
    else:
        if len(id) > 3:
            pid = id[:3]
        else:
            pid = ""
    if id in symbols:
        return toEntry(id, pid, symbols[id], symbols[id])
    return createUnknownEntry(symbols, type, id, pid)

def initDiagnosis():
    return getGlobalSymbols()

### procedure ###

def createProcedureEntry(symbols, type, id):
    pid = "" # find parent id
    if id in symbols:
        return toEntry(id, pid, symbols[id], symbols[id])
    return createUnknownEntry(symbols, type, id)

def initProcedure():
    return getGlobalSymbols()

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

### general lookup table ###

globalSymbols = {}

def getGlobalSymbols():
    global globalSymbols
    if len(globalSymbols.keys()) == 0:
        globalSymbols = initGlobalSymbols()
    return globalSymbols

def initGlobalSymbols():
    codes_dict = {}
    if not os.path.isfile(globalSymbolsFile):
        return codes_dict
    with open(globalSymbolsFile, 'r') as file:
        lines = file.readlines()
    file.close()
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
    input.close()
    return dict

def enrichDict(file, mid):
    if file == sys.stdout or not os.path.isfile(file):
        dict = {}
    else:
        dict = loadOldDict(file)
    with open(mid, 'r') as pfile:
        patient = json.loads(pfile.read())
    pfile.close()
    extractEntries(dict, patient)
    if file == sys.stdout:
        print(json.dumps(dict, indent=2), file=file)
    else:
        with open(file, 'w') as output:
            print(json.dumps(dict, indent=2), file=output)
        output.close()

### argument API

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
        output.close()
        return
    config = {}
    with open(file, 'r') as input:
        config = json.loads(input.read())
    input.close()
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
        'ndc_package': packageFile
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
    productFile = settings['ndc_prod']
    packageFile = settings['ndc_package']
    enrichDict(info['output'], info['mid'])
