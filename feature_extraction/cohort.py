# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/../call.sh" "$0" "$@";" """
from __future__ import print_function
from __future__ import division

import time as time_lib
from datetime import datetime, timedelta
import re
import sys
import os.path
import csv

sys.path.append('..')

import build_dictionary
import cms_get_patient
import util

__doc__ = """
Created on 2015-03-08

@author: joschi
"""

debug_inspect = False
inspect_pids = set([
    'ADEDFB0ACC2513AD',
    'FEE931854890F1F0'
])

class Range:
    """TODO"""
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __str__(self):
        return "[{0}:{1}]".format(repr(self.start), repr(self.end))

    def inRange(self, value):
        if self.start is None:
            return self.end > value if self.end is not None else True
        elif self.start > value:
            return False
        return self.end > value if self.end is not None else True

class Candidate:
    """TODO"""
    def __init__(self, pid):
        self.pid = pid
        self.mem = {}

    def getMem(self, qmId):
        return self.mem[qmId] if qmId in self.mem else {}

    def setMem(self, qmId, obj):
        self.mem[qmId] = obj

    def getPid(self):
        return self.pid

class QueryMatcher:
    """TODO"""
    qmId = 0

    def __init__(self, processCB, matchCB):
        self.processCB = processCB
        self.matchCB = matchCB
        self.children = []
        self.id = QueryMatcher.qmId
        QueryMatcher.qmId += 1

    def addChild(self, qm):
        self.children.append(qm)

    def processEvent(self, candidate, event):
        self.processCB(self.id, self.children, candidate, event)

    def isMatch(self, candidate):
        return self.matchCB(self.id, self.children, candidate)

class ParseException(Exception):
    def __init__(self, start, end, query, msg):
        self.start = start
        self.end = end
        self.query = query
        self.msg = msg
        self.message = str(self)

    def __str__(self):
        res = "{0} at ({1}:{2})".format(self.msg, self.start, self.end)
        q = self.query
        start = self.start
        end = self.end
        before = q[:start]
        middle = q[start:end]
        after  = q[end:]
        context = 20
        ws = "\n" # TODO handle other white space characters
        before = before[ max(before.rfind(ws) + 1, len(before) - context) :]
        aix = after.find(ws)
        after = after[: min(aix, context) if aix >= 0 else context ]
        line = before + middle + after
        last = " " * len(before) + ("^" if not len(middle) else "^" + "~" * (len(middle) - 1))
        return res + "\n" + line + "\n" + last

### grammar
# identifiers: <group>, <id>, <date>, <number>
# reserved characters: " ", "(", ")", "|", "@", ",", "<", ">", "=", "-", ":", "!"
# <ids>: <id> | "(" <id> { "|" <id> }* ")"
# <type>: <group> ":" <ids> | "age" ":" <ranges> "@" <date>
# <types>: <type> | "(" <type> { "|" <type> }* ")"
# <range>: <number> { "-" <number> }? | <cmp> <number>
# <ranges>: <range> | "(" <range> { "|" <range> }* ")"
# <cmp>: { "<" | ">" } { "=" }?
# <time>: <date> { "-" <date> }? | <cmp> <date>
# <times>: <time> | "(" <time> { "|" <time> }* ")"
# <rule>: { "!" }? <types> { "@" <times> }?
# <rules>: <rule> | "(" <rule> { "|" <rule> }* ")"
# <query>: <rules> { "," <rules> }*

def parseQuery(query):
    class State:
        q = query
        pos = 0
    nonWS = re.compile(r"[^\s]")
    reserved = re.compile(r"[\s()|@,<>=:!-]")

    def err(start, end, msg):
        raise ParseException(start, end, query, msg)

    def move(by):
        res = State.q[:by]
        State.q = State.q[by:]
        State.pos += by
        return res

    def chompWS():
        ix = nonWS.search(State.q)
        if ix is not None:
            move(ix.start())

    # <group>, <id>
    def literal():
        chompWS()
        ix = reserved.search(State.q)
        res = move(len(State.q)) if ix is None else move(ix.start())
        if res == "":
            err(State.pos, State.pos, "expected literal")
        return res

    # <date>
    def date():
        lit = literal()
        try:
            return util.toTime(lit)
        except Exception, e:
            err(State.pos - len(lit), State.pos, "cannot convert to date: " + str(e))

    # <number>
    def number():
        lit = literal()
        try:
            return int(lit)
        except Exception, e:
            err(State.pos - len(lit), State.pos, "cannot convert to number: " + str(e))

    # reserved characters
    def char(c):
        chompWS()
        if not len(State.q):
            err(State.pos, State.pos, "unexpected EOF. expected '{0}'".format(c))
        if c != State.q[0]:
            err(State.pos, State.pos, "expected '{0}'".format(c))
        move(1)
        return c

    def peek(c):
        chompWS()
        if not len(State.q):
            return False
        return State.q[0] == c

    def parse_disjunction(between):
        if not peek("("):
            between()
            return
        char("(")
        between()
        while peek("|"):
            char("|")
            between()
        char(")")

    # <ids>: <id> | "(" <id> { "|" <id> }* ")"
    def ids():
        res = []

        def addId():
            lit = literal()
            res.append(lit)
            if "__" in lit:
                res.append(lit.split("__", 1)[1])

        parse_disjunction(addId)
        return res

    # <type>: <group> ":" <ids> | "age" ":" <ranges> "@" <date>
    def type():
        group = literal()
        if group == "age":
            char(":")
            rs = ranges()
            char("@")
            d = date()
            return {
                "group": "info",
                "id": "age",
                "ranges": rs,
                "date": d
            }
        char(":")
        id_list = ids()
        return {
            "group": group,
            "id": id_list,
        }

    # <types>: <type> | "(" <type> { "|" <type> }* ")"
    def types():
        res = []
        parse_disjunction(lambda: res.append(type()))
        return res

    # <range>: <number> { "-" <number> }? | <cmp> <number>
    def range():
        if peek("<") or peek(">"):
            c = cmp()
            num = number()
            return {
                "<": Range(None, num),
                "<=": Range(None, num + 1),
                ">": Range(num + 1, None),
                ">=": Range(num, None)
            }[c]
        start = number()
        if peek("-"):
            char("-")
            end = number()
            return Range(start, end + 1)
        return Range(start, start + 1)

    # <ranges>: <range> | "(" <range> { "|" <range> }* ")"
    def ranges():
        res = []
        parse_disjunction(lambda: res.append(range()))
        return res

    # <cmp>: { "<" | ">" } { "=" }?
    def cmp():
        res = ""
        if peek("<"):
            res += char("<")
        else:
            res += char(">")
        if peek("="):
            res += char("=")
        return res

    # <time>: <date> { "-" <date> }? | <cmp> <date>
    def time():
        if peek("<") or peek(">"):
            c = cmp()
            d = date()
            return {
                "<": Range(None, d),
                "<=": Range(None, util.nextDay(d)),
                ">": Range(util.nextDay(d), None),
                ">=": Range(d, None)
            }[c]
        start = date()
        if peek("-"):
            char("-")
            end = date()
            return Range(start, util.nextDay(end))
        return Range(start, util.nextDay(start))

    # <times>: <time> | "(" <time> { "|" <time> }* ")"
    def times():
        res = []
        parse_disjunction(lambda: res.append(time()))
        return res

    # <rule>: { "!" }? <types> { "@" <times> }?
    def rule():
        negate = False
        if peek("!"):
            char("!")
            negate = True
        ts = types()
        trs = [ Range(None, None) ]
        if peek("@"):
            char("@")
            trs = times()

        def process(id, children, candidate, event):
            if "match" in candidate.getMem(id):
                return
            groupId = event["group"]
            typeId = event["id"]

            def checkType(t):
                group = t["group"]
                if group == "info":
                    raise NotImplementedError("special casing for special types")
                if group != groupId:
                    return False

                def check(tid):
                    res = typeId.startswith(tid)
                    if debug_inspect and candidate.pid in inspect_pids:
                        print("{0} {1} {2} {3} {4}".format(repr(typeId), repr(tid), repr(res), repr(candidate.pid), repr(negate)), file=sys.stderr)
                    return res

                return any(check(tid) for tid in t["id"])

            if not any(checkType(t) for t in ts):
                return
            time = event["time"]

            def checkTime(r):
                res = r.inRange(time)
                if debug_inspect and candidate.pid in inspect_pids:
                    print("{0} {1} {2} {3} {4} {5}".format(repr(time), str(r), repr(res), repr(typeId), repr(candidate.pid), repr(negate)), file=sys.stderr)
                return res

            if not any(checkTime(r) for r in trs):
                return
            candidate.setMem(id, {
                "match": True
            })

        def match(id, children, candidate):
            return negate != ("match" in candidate.getMem(id))

        return QueryMatcher(process, match)

    # <rules>: <rule> | "(" <rule> { "|" <rule> }* ")"
    def rules():

        def process(id, children, candidate, event):
            for c in children:
                c.processEvent(candidate, event)

        def match(id, children, candidate):
            return any(c.isMatch(candidate) for c in children)

        res = QueryMatcher(process, match)
        parse_disjunction(lambda: res.addChild(rule()))
        return res

    # <query>: <rules> { "," <rules> }*
    def pQuery():

        def process(id, children, candidate, event):
            for c in children:
                c.processEvent(candidate, event)

        def match(id, children, candidate):
            return all(c.isMatch(candidate) for c in children)

        res = QueryMatcher(process, match)
        res.addChild(rules())
        while peek(","):
            char(",")
            res.addChild(rules())
        return res

    return pQuery()

def handleRow(row, id, eventCache, infoCache):
    obj = {
        "info": [],
        "events": []
    }
    cms_get_patient.handleRow(row, obj)
    eventCache.extend(obj["events"])
    """ FIXME no info handling yet
    for info in obj["info"]:
        if info["id"] == "age":
            try:
                bin = (int(info["value"]) // age_bin) * age_bin
                infoCache.append("age_" + str(bin) + "_" + str(bin + age_bin))
            except ValueError:
                pass
        elif info["id"] == "born":
            try:
                if info["value"] != "N/A" and age_time is not None:
                    bin = (toAge(info["value"]) // age_bin) * age_bin
                    infoCache.append("age_" + str(bin) + "_" + str(bin + age_bin))
            except ValueError:
                pass
        elif info["id"] == "death" and info["value"] != "N/A":
            infoCache.append("dead")
        elif info["id"] == "gender":
            if info["value"] == "M":
                infoCache.append("sex_m")
            elif info["value"] == "F":
                infoCache.append("sex_f")
    """

def processFile(inputFile, id_column, qm, candidates, printInfo):
    if printInfo:
        print("processing file: {0}".format(inputFile), file=sys.stderr)
    id_event_cache = {}
    id_info_cache = {}

    def handleRows(csvDictReader):
        for row in csvDictReader:
            id = row[id_column]
            if id in id_event_cache:
                eventCache = id_event_cache[id]
            else:
                eventCache = []
            if id in id_info_cache:
                infoCache = id_info_cache[id]
            else:
                infoCache = []
            handleRow(row, id, eventCache, infoCache)
            id_event_cache[id] = eventCache
            if len(infoCache) > 0:
                id_info_cache[id] = infoCache

    def processDict(events, id):
        if len(events) == 0:
            return
        if id not in candidates:
            candidates[id] = Candidate(id)
        candidate = candidates[id]
        for e in events:
            qm.processEvent(candidate, e)
        """ FIXME no hierarchy handling yet
        print("processing {1} with {0} events".format(len(events), id), file=sys.stderr)
        obj = {
            "events": events
        }
        dict = {}
        build_dictionary.extractEntries(dict, obj)
        for group in dict.keys():
            cb(id, group, dict[group].keys())
        """
        if debug_inspect and id in inspect_pids:
            print("{0} {1}".format(qm.isMatch(candidate), id), file=sys.stderr)

    if inputFile == '-':
        handleRows(csv.DictReader(sys.stdin))
    else:
        with open(inputFile) as csvFile:
            handleRows(csv.DictReader(csvFile))

    num_total = len(id_event_cache.keys())
    num = 0
    for id in id_event_cache.keys():
        eventCache = id_event_cache[id]
        processDict(eventCache, id)
        del eventCache[:]
        num += 1
        if not debug_inspect and printInfo and sys.stderr.isatty():
            sys.stderr.write("processing: {0:.2%}\r".format(num / num_total))
            sys.stderr.flush()
    if not debug_inspect and printInfo and sys.stderr.isatty():
        print("", file=sys.stderr)
    """ FIXME no info handling yet
    for id in id_info_cache.keys():
        infoCache = id_info_cache[id]
        cb(id, "info", infoCache)
    """

def processAll(qm, cohort, path_tuples):
    candidates = {}
    id_column = cms_get_patient.input_format["patient_id"]
    for (path, isfile) in path_tuples:
        if isfile:
            processFile(path, id_column, qm, candidates, not debug_inspect)
        else:
            util.process_directory(path, lambda file, printInfo: processFile(file, id_column, qm, candidates, not debug_inspect and printInfo), not debug_inspect)
    for c in candidates.values():
        if qm.isMatch(c):
            cohort.append(c.getPid())
    cohort.sort()

def printResult(cohort, out):
    for c in cohort:
        print(c, file=out)

def usage():
    print('usage: {0} [-h|--debug] [-o <output>] -f <format> -c <config> -q <query> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('usage: {0} [-h|--debug] [-o <output>] -f <format> -c <config> --query-file <file> -- <file or path>...'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('--debug: prints debug output', file=sys.stderr)
    print('-o <output>: specifies output file. stdout if omitted or "-"', file=sys.stderr)
    print('-f <format>: specifies table format file', file=sys.stderr)
    print('-c <config>: specify config file', file=sys.stderr)
    print('-q <query>: specifies the query', file=sys.stderr)
    print('--query-file <file>: specifies a file containing the query', file=sys.stderr)
    print('<file or path>: a list of input files or paths containing them. "-" represents stdin', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    output = '-'
    settingsFile = None
    settings = {}
    settings['delim'] = ','
    settings['quote'] = '"'
    query = ""
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '--':
            break
        if arg == '-h':
            usage()
        elif arg == '-q':
            if not args or args[0] == '--':
                print('-q requires query', file=sys.stderr)
                usage()
            if len(query):
                print('only one query allowed', file=sys.stderr)
                usage()
            query = args.pop(0)
        elif arg == '--query-file':
            if not args or args[0] == '--':
                print('--query-file requires file', file=sys.stderr)
                usage()
            if len(query):
                print('only one query allowed', file=sys.stderr)
                usage()
            with open(args.pop(0), 'r') as qf:
                query = qf.read()
        elif arg == '-f':
            if not args or args[0] == '--':
                print('-f requires format file', file=sys.stderr)
                usage()
            util.read_format(args.pop(0), cms_get_patient.input_format, usage)
        elif arg == '-o':
            if not args or args[0] == '--':
                print('-o requires output file', file=sys.stderr)
                usage()
            output = args.pop(0)
        elif arg == '-c':
            if not args or args[0] == '--':
                print('-c requires argument', file=sys.stderr)
                usage()
            settingsFile = args.pop(0)
            util.read_config(settings, settingsFile, build_dictionary.debugOutput)
        elif arg == '--debug':
            build_dictionary.debugOutput = True
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    if not len(query):
        print('query is required', file=sys.stderr)
        usage()

    build_dictionary.init(settings, settingsFile)

    allPaths = []
    while args:
        path = args.pop(0)
        if os.path.isfile(path) or path == '-':
            allPaths.append((path, True))
        elif os.path.isdir(path):
            allPaths.append((path, False))
        else:
            print('illegal argument: '+path+' is neither file nor directory', file=sys.stderr)

    qm = parseQuery(query)
    cohort = []
    processAll(qm, cohort, allPaths)
    with util.OutWrapper(output) as out:
        printResult(cohort, out)
