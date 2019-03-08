# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@";" """
from __future__ import print_function

import os
import sys
import json

def usage():
    print("""
usage: {0} [-h] [-bc] -f <file> -- <key> <value>...
-h: print help
-b: boolean values
-c: allow creating a new file
-f <file>: the file containing the JSON
<key>: the key
<value>: the value to set

""".strip().format(sys.argv[0]), file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    ufile = None
    bool_values = False
    create = False
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '-h':
            usage()
        elif arg == '--':
            break
        elif arg == '-c':
            create = True
        elif arg == '-b':
            bool_values = True
        elif arg == '-f':
            if not args:
                print("-f requires argument", file=sys.stderr)
                usage()
            ufile = args.pop(0)
        else:
            print("unknown argument: {0}".format(arg), file=sys.stderr)
            usage()
    if ufile is None:
        print("must specify file", file=sys.stderr)
        usage()
    obj = {}
    if os.path.isfile(ufile):
        with open(ufile, 'r') as f:
            obj = json.load(f)
    elif not create:
        print("'{0}' is not a file".format(ufile), file=sys.stderr)
        usage()
    while args:
        key = args.pop(0)
        if not args:
            print("missing value for key: {0}".format(key), file=sys.stderr)
        value = args.pop(0)
        value = value if not bool_values else value == 'true'
        obj[key] = value
    with open(ufile, 'w') as f:
        print(json.dumps(obj, indent=2, sort_keys=True), file=f)
