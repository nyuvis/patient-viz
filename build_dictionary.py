# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@"; """
from __future__ import print_function

import time
import datetime
import shelve
from datetime import datetime,timedelta
import sys
import csv
import json
import os.path

import util

__doc__ = """
Created on Mon Oct 13 11:44:00 2014

@author: joschi
@author: razavian
"""

debugOutput = False

class EntryCreator(object):
    def __init__(self):
        self._baseTypes = {}
        self._codeTables = {}
        self._unknown = None

    def baseType(self, name):
        def wrapper(cls):
            obj = cls()
            if not isinstance(obj, TypeBase):
                raise TypeError("{0} is not a {1}".format(cls.__name__, TypeBase.__name__))
            self._baseTypes[name] = obj
            return cls
        return wrapper

    def codeType(self, name, code):
        def wrapper(cls):
            obj = cls()
            if not isinstance(obj, TypeCode):
                raise TypeError("{0} is not a {1}".format(cls.__name__, TypeCode.__name__))
            obj.code = code
            self._baseTypes[name].addCodeType(code, obj)
            return cls
        return wrapper

    def unknownType(self):
        def wrapper(cls):
            obj = cls()
            if not isinstance(obj, TypeBase):
                raise TypeError("{0} is not a {1}".format(cls.__name__, TypeBase.__name__))
            self._unknown = obj
        return wrapper

    def createEntry(self, dict, type, id, onlyAddMapped=False, code=None):
        if not id:
            entry = self.createRootEntry(type)
        else:
            baseType = self._baseTypes.get(type, self._unknown)
            symbols = self._codeTables.get(type, {})
            (entry, code) = baseType.create(symbols, type, id, code)
        if type not in dict:
            dict[type] = {}
        if onlyAddMapped and 'unmapped' in entry and entry['unmapped']:
            return
        dict[type][id] = entry
        pid = entry['parent']
        if pid not in dict[type]:
            self.createEntry(dict, type, pid, False, code)
        if 'alias' in entry:
            aid = entry['alias']
            if aid not in dict[type]:
                self.createEntry(dict, type, aid, True, code)

    def createRootEntry(self, type):
        baseType = self._baseTypes.get(type, self._unknown)
        name = baseType.name()
        if name == UNKNOWN:
            name += " " + type
        desc = baseType.desc()
        if desc == UNKNOWN:
            desc += " " + type
        res = toEntry("", "", name, desc)
        res["color"] = baseType.color()
        flags = baseType.flags()
        if len(flags.keys()):
            res["flags"] = flags
        return res

    def init(self, settings, settingsFile):
    	for k in self._baseTypes.keys():
            self._codeTables[k] = self._baseTypes[k].init(settings)
        util.save_config(settings, settingsFile)

dictionary = EntryCreator()

class TypeBase(object):
    def __init__(self):
        self._codeTypes = {}
    def name(self):
        raise NotImplementedError()
    def desc(self):
        return self.name()
    def color(self):
        raise NotImplementedError()
    def flags(self):
        return {}
    def addCodeType(self, code, codeType):
        self._codeTypes[code] = codeType
    def init(self, settings):
        res = {}
        for code in self._codeTypes.keys():
            res[code] = self._codeTypes[code].init(settings)
        return res
    def create(self, symbols, type, id, code):
        candidate = None
        if "__" in id:
            [ new_code, id ] = id.split("__", 1)
            if new_code in self._codeTypes.keys():
                code = new_code
            elif debugOutput:
                print("unknown code {0} in id '{1}' using {2}".format(repr(new_code), repr(new_code + "__" + id), repr(code), file=sys.stderr))
        if code is not None:
            if code in self._codeTypes and code in symbols:
                candidate = self._codeTypes[code].create(symbols[code], type, id)
            elif debugOutput:
                print("unknown code {0}".format(repr(code), file=sys.stderr))
        else:
            for k in self._codeTypes.keys():
                can = self._codeTypes[k].create(symbols[k], type, id)
                if candidate is not None:
                    umOld = "unmapped" in candidate and candidate["unmapped"]
                    um = "unmapped" in can and can["unmapped"]
                    if um and not umOld:
                        continue
                    if um == umOld:
                        candidate = None
                        if not um and debugOutput:
                            print("ambiguous type {0} != {1}".format(repr(candidate), repr(can), file=sys.stderr))
                        break
                candidate = can
        if candidate is None:
            return (createUnknownEntry({}, type, id, code=code), code)
        return (candidate, code)

class TypeCode(object):
    def init(self, settings):
        raise NotImplementedError()
    def create(self, symbols, type, id):
        raise NotImplementedError

### provider ###
@dictionary.baseType("provider")
class TypeProvider(TypeBase):
    def name(self):
        return "Provider"
    def color(self):
        return "#e6ab02"

@dictionary.codeType("provider", "cms")
class CmsProviderCode(TypeCode):
    def create(self, symbols, type, id):
        pid = id[2:4] if len(id) >= 4 else ""
        if id in symbols:
            return toEntry(id, pid, symbols[id], symbols[id])
        if len(id) == 2:
            return createUnknownEntry(symbols, type, id, pid, code=self.code)
        return toEntry(id, pid, id, "Provider Number: {0}".format(id))
    def init(self, settings):
        res = {}
        file = get_file(settings, 'pnt', 'code/pnt/pnt.txt')
        if not os.path.isfile(file):
            return res
        with open(file, 'r') as pnt:
            for line in pnt.readlines():
                l = line.strip()
                if len(l) < 10 or not l[0].isdigit() or not l[1].isdigit() or not l[5].isdigit() or not l[6].isdigit():
                    continue
                fromPN = int(l[0:2])
                toPN = int(l[5:7])
                desc = l[9:].strip()
                for pn in xrange(fromPN, toPN + 1):
                    res[("00" + str(pn))[-2:]] = desc
        return res

### physician ###
@dictionary.baseType("physician")
class TypePhysician(TypeBase):
    def name(self):
        return "Physician"
    def color(self):
        return "#fccde5"

@dictionary.codeType("physician", "cms")
class CmsPhysicianCode(TypeCode):
    def create(self, symbols, type, id):
        pid = ""
        return createUnknownEntry(symbols, type, id, pid, code=self.code)
    def init(self, settings):
        return {}

@dictionary.codeType("physician", "alt")
class CmsPhysicianCode(TypeCode):
    def create(self, symbols, type, id):
        pid = ""
        if id in symbols:
            return toEntry(id, pid, symbols[id], symbols[id])
        return createUnknownEntry(symbols, type, id, pid, code=self.code)
    def init(self, settings):
        res = {}
        spec_file = get_file(settings, 'alt_speciality', 'code/specialty/specialty_headers.txt')
        if os.path.isfile(spec_file):
            with open(spec_file, 'r') as file:
                for line in file:
                    l = line.strip()
                    spl = l.split('#', 1)
                    if len(spl) < 2:
                        continue
                    res[spl[0]] = spl[1]
        return res

### prescribed ###
@dictionary.baseType("prescribed")
class TypePrescribed(TypeBase):
    def name(self):
        return "Prescribed Medication"
    def color(self):
        return "#eb9adb"

@dictionary.codeType("prescribed", "ndc")
class NdcPrescribedCode(TypeCode):
    def create(self, symbols, type, id):
        pid = id[:-2] if len(id) == 11 else ""
        if id in symbols:
            l = symbols[id]
            return toEntry(id, pid, l["nonp"], l["nonp"]+" ["+l["desc"]+"] ("+l["prop"]+") "+l["subst"]+" - "+l["pharm"]+" - "+l["pType"], l["alias"] if "alias" in l else None)
        return createUnknownEntry(symbols, type, id, pid, code=self.code)
    def init(self, settings):
        uidLookup = {}
        file_main = get_file(settings, 'ndc', '')
        if file_main and os.path.isfile(file_main):
            with open(file_main, 'r') as fm:
                for line in fm.readlines():
                    if '---' not in line:
                        continue
                    key, name = line.split('---', 1)
                    uidLookup[key.strip()] = {
                        "pType": '',
                        "prop": '',
                        "nonp": name.strip(),
                        "subst": '',
                        "pharm": '',
                        "desc": ''
                    }
            return uidLookup
        fileA = get_file(settings, 'ndc_prod', 'code/ndc/product.txt')
        if not os.path.isfile(fileA):
            return uidLookup
        prescribeLookup = {}
        with open(fileA, 'r') as prFile:
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
                subst = row['SUBSTANCENAME'].strip() if row['SUBSTANCENAME'] is not None else ""
                pharm = row['PHARM_CLASSES'].strip() if row['PHARM_CLASSES'] is not None else ""
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
                    "pharm": l["pharm"],
                    "alias": normndc
                }
                prescribeLookup[ndc] = obj
                prescribeLookup[normndc] = obj
                prescribeLookup[fullndc] = obj
        fileB = get_file(settings, 'ndc_package', 'code/ndc/package.txt')
        if not os.path.isfile(fileB):
            return prescribeLookup
        with open(fileB, 'r') as paFile:
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
                    "pharm": l["pharm"],
                    "alias": normndc
                }
                prescribeLookup[ndc] = obj
                prescribeLookup[normndc] = obj
                prescribeLookup[fullndc] = obj
        return prescribeLookup

### lab-test ###
@dictionary.baseType("lab-test")
class TypeLabtest(TypeBase):
    def name(self):
        return "Laboratory Test"
    def color(self):
        return "#80b1d3"
    def flags(self):
        return {
            "L": {
                "color": "#fb8072"
            },
            "H": {
                "color": "#fb8072"
            },
        }

@dictionary.codeType("lab-test", "loinc")
class LoincLabtestCode(TypeCode):
    def create(self, symbols, type, id):
        pid = "" # find parent id
        if id in symbols:
            return toEntry(id, pid, symbols[id], symbols[id])
        return createUnknownEntry(symbols, type, id, pid, code=self.code)
    def init(self, settings):
        res = getGlobalSymbols(settings)
        loinc_file = get_file(settings, 'loinc', 'code/loinc/loinc_file.all.headers')
        if os.path.isfile(loinc_file):
            with open(loinc_file, 'r') as file:
                for line in file:
                    l = line.strip()
                    spl = l.split('#', 1)
                    if len(spl) < 2:
                        continue
                    res[spl[0]] = spl[1]
        return res

### diagnosis ###
@dictionary.baseType("diagnosis")
class TypeDiagnosis(TypeBase):
    def name(self):
        return "Condition"
    def color(self):
        return "#4daf4a"

@dictionary.codeType("diagnosis", "icd9")
class Icd9DiagnosisCode(TypeCode):
    def __init__(self):
        self._parents = {}
    def create(self, symbols, type, id):
        prox_id = id
        pid = ""
        while len(prox_id) >= 3:
            pid = self._parents[prox_id] if prox_id in self._parents else pid
            if prox_id in symbols:
                return toEntry(id, pid, symbols[prox_id], symbols[prox_id], id.replace(".", "") if "HIERARCHY" not in id else None)
            prox_id = prox_id[:-1]
        return createUnknownEntry(symbols, type, id, pid, code=self.code)
    def init(self, settings):
        codes = getGlobalSymbols(settings)
        codes.update(getICD9(settings, True))
        self._parents = util.read_CCS(get_file(settings, 'ccs_diag', 'code/ccs/multi_diag.txt'), codes)
        return codes

### procedure ###
@dictionary.baseType("procedure")
class TypeProcedure(TypeBase):
    def name(self):
        return "Procedure"
    def color(self):
        return "#ff7f00"

@dictionary.codeType("procedure", "icd9")
class Icd9ProcedureCode(TypeCode):
    def __init__(self):
        self._parents = {}
    def create(self, symbols, type, id):
        prox_id = id
        pid = ""
        while len(prox_id) >= 3:
            pid = self._parents[prox_id] if prox_id in self._parents else pid
            if prox_id in symbols:
                return toEntry(id, pid, symbols[prox_id], symbols[prox_id], id.replace(".", "") if "HIERARCHY" not in id else None)
            prox_id = prox_id[:-1]
        return createUnknownEntry(symbols, type, id, pid)
    def init(self, settings):
        codes = getGlobalSymbols(settings)
        codes.update(getICD9(settings, False))
        self._parents = util.read_CCS(get_file(settings, 'ccs_proc', 'code/ccs/multi_proc.txt'), codes)
        return codes

@dictionary.codeType("procedure", "cpt")
class CPTProcedureCode(TypeCode):
    def create(self, symbols, type, id):
        pid = ""
        if id in symbols:
            return toEntry(id, pid, symbols[id], symbols[id], None)
        return createUnknownEntry(symbols, type, id, pid)
    def init(self, settings):
        file = get_file(settings, 'procedure_cpt_long', 'code/cpt/cpt_codes_long_descr.csv')
        codes = {}
        if not os.path.isfile(file):
            return codes
        with open(file, 'r') as f:
            for row in csv.DictReader(f):
                key = row['CPT_CODE']
                value = row['CPT_LONG_DESCRIPTION']
                if not key or not value:
                    continue
                codes[key.strip()] = value.strip()
        return codes

### info ###
@dictionary.baseType("info")
class TypeInfo(TypeBase):
    def name(self):
        return "Info"
    def color(self):
        return "pink"

@dictionary.codeType("info", "info")
class InfoInfoCode(TypeCode):
    def create(self, symbols, type, id):
        pid = ""
        return toEntry(id, pid, id, "Info: " + id)
    def init(self, settings):
        return {}


### unknown ###
UNKNOWN = "UNKNOWN"

@dictionary.unknownType()
class TypeUnknown(TypeBase):
    def name(self):
        return UNKNOWN
    def color(self):
        return "red"
    def init(self, settings):
        raise NotImplementedError()
    def create(self, symbols, type, id, code):
        return createUnknownEntry(symbols, type, id, code=code)

def createUnknownEntry(_, type, id, pid = "", code = None):
    # TODO remove: can be seen by attribute unmapped
    #if debugOutput:
    #    print("unknown entry; type: " + type + " id: " + id, file=sys.stderr)
    if "__" in id:
      (code, id) = id.split("__", 1)
    typeText = type + " (" + code + ")" if code is not None else type
    res = toEntry(id, pid, id, typeText + " " + id)
    res["unmapped"] = True
    return res

def toEntry(id, pid, name, desc, alias=None):
    res = {
        "id": id,
        "parent": pid,
        "name": name,
        "desc": desc
    }
    if alias is not None and alias != id:
        res["alias"] = alias
    return res

### icd9 ###

globalICD9 = {
    'diagnosis': {},
    'procedure': {}
}

def getICD9(settings, isDiagnosis):
    k = 'diagnosis' if isDiagnosis else 'procedure'
    if not len(globalICD9[k].keys()):
        fileKeyS = k + '_icd9'
        fileKeyL = k + '_icd9_long'
        fileDefaultS = 'code/icd9/' + ('CMS32_DESC_SHORT_DX.txt' if isDiagnosis else 'CMS32_DESC_SHORT_SG.txt')
        fileDefaultL = 'code/icd9/' + ('CMS32_DESC_LONG_DX.txt' if isDiagnosis else 'CMS32_DESC_LONG_SG.txt')
        fileS = get_file(settings, fileKeyS, fileDefaultS)
        fileL = get_file(settings, fileKeyL, fileDefaultL)
        if not os.path.isfile(fileS) and not os.path.isfile(fileL):
            globalICD9[k] = initICD9(settings)
        else:
            symbols = globalICD9[k]
            f = fileS if not os.path.isfile(fileL) else fileL
            with open(f, 'r') as file:
                for line in file:
                    l = line.strip()
                    spl = l.split(' ', 1)
                    if len(spl) < 2:
                        continue
                    key = spl[0].strip()
                    value = spl[1].strip()
                    if len(key) > 3:
                        key_dot = key[:3] + '.' + key[3:]
                        symbols[key_dot] = value
                    symbols[key] = value
    return globalICD9[k].copy()

def initICD9(settings):
    codes = {}
    f = get_file(settings, 'icd9', 'code/icd9/ucod.txt')
    if not os.path.isfile(f):
        return codes
    with open(f, 'r') as file:
        lastCode = ""
        for line in file:
            if len(line.strip()) < 2:
                lastCode = ""
                continue
            if not line[1].isdigit():
                if line[0] == ' ' and lastCode != "":
                    noDot = lastCode.replace(".", "")
                    codes[lastCode] = codes[lastCode] + " " + line.strip().rstrip('- ').rstrip()
                    codes[noDot] = codes[noDot] + " " + line.strip().rstrip('- ').rstrip()
                continue
            spl = line.split(None, 1)
            if len(spl) == 2:
                lastCode = spl[0].strip()
                noDot = lastCode.replace(".", "")
                codes[lastCode] = spl[1].rstrip().rstrip('- ').rstrip()
                codes[noDot] = spl[1].rstrip().rstrip('- ').rstrip()
            else:
                if line[0] != '(':
                    print("invalid ICD9 line: '" + line.rstrip() + "'", file=sys.stderr)
    return codes

### general lookup table ###

globalSymbols = {}

def getGlobalSymbols(settings):
    global globalSymbols
    if not len(globalSymbols.keys()):
        globalSymbols = initGlobalSymbols(settings)
    return globalSymbols.copy()

def initGlobalSymbols(settings):
    codes_dict = {}
    f = get_file(settings, 'filename', 'code/code_names.txt')
    if not os.path.isfile(f):
        return codes_dict
    with open(f, 'r') as file:
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
        dictionary.createEntry(dict, event['group'], event['id'])

def loadOldDict(file):
    dict = {}
    if file == '-' or not os.path.isfile(file):
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
    with util.OutWrapper(file) as out:
        print(json.dumps(dict, indent=2, sort_keys=True), file=out)

def init(settings, settingsFile):
    dictionary.init(settings, settingsFile)

### argument API

def get_file(settings, key, default):
    if key in settings:
        file = settings[key]
    else:
        file = default
        settings[key] = file
    return util.get_file(file, debugOutput)

def usage():
    print("{0}: [--debug] -p <file> -c <config> -o <output> [-h|--help] [--lookup <id...>]".format(sys.argv[0]), file=sys.stderr)
    print("--debug: prints debug information", file=sys.stderr)
    print("-p <file>: specify patient json file. '-' uses standard in", file=sys.stderr)
    print("-c <config>: specify config file", file=sys.stderr)
    print("-o <output>: specify output file. '-' uses standard out", file=sys.stderr)
    print("--lookup <id...>: lookup mode. translates ids in shorthand notation '${group_id}__${type_id}'. '-' uses standard in with ids separated by spaces", file=sys.stderr)
    print("-h|--help: prints this help.", file=sys.stderr)
    sys.exit(1)

def interpretArgs():
    global debugOutput
    settings = {}
    settingsFile = None
    info = {
        'mid': '-',
        'output': '-'
    }
    lookupMode = False
    args = sys.argv[:]
    args.pop(0)
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
            settingsFile = args.pop(0)
            util.read_config(settings, settingsFile, debugOutput)
        elif val == '-o':
            if not args:
                print('-o requires argument', file=sys.stderr)
                usage()
            info['output'] = args.pop(0)
        elif val == '--lookup':
            lookupMode = True
            break
        elif val == '--debug':
            debugOutput = True
        else:
            print('illegal argument '+val, file=sys.stderr)
            usage()
    return (settings, settingsFile, info, lookupMode, args)

if __name__ == '__main__':
    (settings, settingsFile, info, lookupMode, rest) = interpretArgs()
    dictionary.init(settings, settingsFile)
    if lookupMode:
        edict = {}

        def addEntry(e):
            spl = e.split('__', 1)
            if len(spl) != 2:
                print("shorthand format is '${group_id}__${type_id}': " + e, file=sys.stderr)
                sys.exit(1)
            dictionary.createEntry(edict, spl[0].strip(), spl[1].strip())

        for e in rest:
            if e == "-":
                for eid in sys.stdin.read().split(" "):
                    if len(eid) > 0 and eid != "id" and eid != "outcome" and eid != "test":
                        addEntry(eid)
            else:
                addEntry(e)

        ofile = info['output']
        with util.OutWrapper(ofile) as out:
            print(json.dumps(edict, indent=2, sort_keys=True), file=out)
    else:
        enrichDict(info['output'], info['mid'])
