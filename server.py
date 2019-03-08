# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@";" """
from __future__ import print_function

import os
import sys
import json

from StringIO import StringIO

import build_dictionary
import cms_analyze
import cms_get_patient
import util
from omop import OMOP

sys.path.append('lib')

from quick_server.quick_server import create_server, msg, json_dumps

json_dir = 'json/'
patients_list = 'patients.txt'
dictionary_bind = 'dictionary.json'

def start_server(max_num, settings_file, format_file, class_file, line_file, cms_path, addr, port, debug):
    settings = {}
    util.read_config(settings, settings_file, True)
    use_cache = settings.get('use_cache', True)

    all_paths = []
    input_format = {}
    use_db = False
    omop = None
    if settings.get('omop_use_db', False):
        use_db = True
        omop = OMOP(settings, True)
    else:
        util.convert_paths([ cms_path ], all_paths)

        util.read_format(format_file, input_format, usage)
        cms_analyze.input_format = input_format
        cms_get_patient.input_format = input_format

        build_dictionary.debugOutput = True
        build_dictionary.init(settings, settings_file)

    dictionary_file = os.path.join(json_dir, dictionary_bind)

    patients = set()
    def save_patients():
        if not use_cache:
            return
        with open(patients_list, 'w') as pf:
            pf.write('\n'.join(sorted(list(patients))))
            pf.flush()

    if not os.path.isfile(patients_list) or not use_cache:
        if use_db:
            omop.list_patients(patients, prefix=json_dir, limit=max_num, show_old_ids=True)
        else:
            tf = StringIO()
            cms_analyze.compute(all_paths, {}, False, tf, filter_zero=True)
            tf.flush()
            tf.seek(0)
            lines = tf.readlines()[-max_num:] if max_num is not None else tf.readlines()
            for line in lines:
                patients.add(json_dir + line.strip() + '.json')
        save_patients()

    dictionary = {}
    if use_cache:
        if os.path.isfile(dictionary_file):
            with open(dictionary_file, 'r') as input:
                dictionary = json.loads(input.read())
        else:
            os.makedirs(json_dir)
            # write the initial empty dictionary
            # also ensures that the folder is writeable
            with open(dictionary_file, 'w') as output:
                output.write("{}")

    server = create_server((addr, port))
    server.bind_path('/', '..')

    prefix = '/' + os.path.basename(os.path.normpath(server.base_path))

    server.add_default_white_list()
    server.add_file_patterns([
            prefix + '/' + json_dir + '*',
            prefix + '/' + patients_list
        ], True)
    server.favicon_fallback = 'favicon.ico'
    server.report_slow_requests = True
    if debug:
        server.suppress_noise = True

    @server.text_get(prefix + '/' + patients_list, 0)
    def get_list(req, args):
        return '\n'.join(sorted(list(patients)))

    @server.json_get(prefix + '/' + json_dir, 1)
    def get_patient(req, args):
        pid = args['paths'][0]
        if pid.endswith('.json') and use_db:
            pid = pid[:-len('.json')]
            pid = omop.get_person_id(pid)
        cache_file = os.path.join(json_dir, pid)
        p_name = json_dir + pid.strip()
        if p_name not in patients:
            patients.add(p_name)
            save_patients()
        if pid.endswith('.json'):
            pid = pid[:-len('.json')]
        if not os.path.isfile(cache_file) or not use_cache:
            if use_db:
                patient = omop.get_patient(pid, dictionary, line_file, class_file)
            else:
                patient = cms_get_patient.process(all_paths, line_file, class_file, pid)
                build_dictionary.extractEntries(dictionary, patient)
            if use_cache:
                with open(cache_file, 'w') as pf:
                    pf.write(json_dumps(patient))
                    pf.flush()
            if use_cache:
                with open(dictionary_file, 'w') as output:
                    output.write(json_dumps(dictionary))
                    output.flush()
            return patient
        with open(cache_file, 'r') as pf:
            return json.loads(pf.read())

    @server.json_get(prefix + '/' + dictionary_file)
    def get_dictionary(req, args):
        return dictionary

    msg("starting server at {0}:{1}", addr if addr else 'localhost', port)
    server.serve_forever()
    msg("shutting down..")
    server.server_close()

def usage():
    print("""
usage: {0} [-h] [--debug] [-a <address>] [-p <port>] [-c <file>] [-f <file>] [-s <file>] [-l <file>] [--max-num <number>] [--cms-path <path>]
-h: print help
-a <address>: specifies the server address. default is 'localhost'
-p <port>: specifies the server port. default is '8080'
-c <file>: specifies config file. default is 'config.txt'
-f <file>: specifies table format file. default is 'format.json'
-s <file>: specifies span class file. default is 'style_classes.json'
-l <file>: specifies optional line and span info file
--max-num <number>: specifies the maximal initial size of the patient list
--cms-path <path>: specifies the path to CMS compatible files
--debug: only report unsuccessful requests
""".strip().format(sys.argv[0]), file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    max_num = 100
    settings_file = 'config.txt'
    format_file = 'format.json'
    class_file = 'style_classes.json'
    line_file = None
    cms_path = 'cms/'
    addr = ''
    port = 8080
    debug = False
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '-h':
            usage()
        elif arg == '-a':
            if not args:
                print('expected argument for -a', file=sys.stderr)
                usage()
            addr = args.pop(0)
        elif arg == '-p':
            if not args:
                print('expected argument for -p', file=sys.stderr)
                usage()
            port = int(args.pop(0))
        elif arg == '-c':
            if not args:
                print('expected argument for -c', file=sys.stderr)
                usage()
            settings_file = args.pop(0)
        elif arg == '-f':
            if not args:
                print('expected argument for -f', file=sys.stderr)
                usage()
            format_file = args.pop(0)
        elif arg == '-s':
            if not args:
                print('expected argument for -s', file=sys.stderr)
                usage()
            class_file = args.pop(0)
        elif arg == '-l':
            if not args:
                print('expected argument for -l', file=sys.stderr)
                usage()
            line_file = args.pop(0)
        elif arg == '--max-num':
            if not args:
                print('expected argument for --max-num', file=sys.stderr)
                usage()
            max_num = int(args.pop(0))
        elif arg == '--cms-path':
            if not args:
                print('expected argument for --cms-path', file=sys.stderr)
                usage()
            cms_path = args.pop(0)
        elif arg == '--debug':
            debug = True
        else:
            print('illegal argument: '+arg, file=sys.stderr)
            usage()
    start_server(max_num, settings_file, format_file, class_file, line_file, cms_path, addr, port, debug)
