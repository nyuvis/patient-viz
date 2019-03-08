# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@"; """

from __future__ import print_function

import os
import sys
import json

import util

def get_name(dict, gid, tid):
    rid = tid.split("__", 2)[1] if "__" in tid else tid
    if gid in dict and tid in dict[gid]:
        type = dict[gid][tid]
        if "alias" in type and type["alias"] != tid and type["alias"] in dict[gid]:
            return get_name(dict, gid, type["alias"])
        desc = type["desc"] if type["desc"] else type["name"]
        if gid != "diagnosis" and gid != "procedure":
            return desc
        if rid.startswith("HIERARCHY") or not rid:
            return desc
        if desc == rid:
            desc = ""
        if '.' in rid:
            return rid + (": " + desc if desc else "")
        letterstart = rid[0].isdigit()
        pre = rid[0:4 if letterstart else 3]
        post = rid[4 if letterstart else 3:]
        return pre + "." + post + (": " + desc if desc else "")
    else:
        return rid

def enrich(dict, obj):
    for e in obj["events"]:
        gid = e["group"]
        tid = e["id"]
        name = get_name(dict, gid, tid)
        if "flag_value" in e:
            add = e["flag_value"] + (" ["+e["flag"]+"]" if "flag" in e else "") + ": ";
        else:
            add = ""
        e["name"] = add + name
    return obj

def usage():
    print("""
usage: {0} [-h] -d <dictionary> [-f <file>] [-o <file>]
-h: print help
-d <dictionary>: the dictionary file
-f <file>: the input file. default is '-' ie STD_IN
-o <file>: the output file. default is '-' ie STD_OUT
""".strip().format(sys.argv[0]), file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    dictionary = None
    input = '-'
    output = '-'
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '-h':
            usage()
        elif arg == '-d':
            if not args:
                print("-d requires argument", file=sys.stderr)
                usage()
            dictionary = args.pop(0)
        elif arg == '-f':
            if not args:
                print("-f requires argument", file=sys.stderr)
                usage()
            input = args.pop(0)
        elif arg == '-o':
            if not args:
                print("-o requires argument", file=sys.stderr)
                usage()
            output = args.pop(0)
        else:
            print("unknown argument: {0}".format(arg), file=sys.stderr)
            usage()
    if dictionary is None:
        print("must specify dictionary", file=sys.stderr)
        usage()
    with open(dictionary, 'r') as d:
        edict = json.load(d)
    obj = {}
    if input == '-':
        obj = json.load(sys.stdin)
    else:
        with open(input, 'r') as f:
            obj = json.load(f)
    obj = enrich(edict, obj)
    with util.OutWrapper(output) as out:
        print(json.dumps(obj, indent=2, sort_keys=True), file=out)
