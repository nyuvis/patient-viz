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

max_num = 100
settings_file = 'config.txt'
format_file = 'format.json'
class_file = 'style_classes.json'
line_file = None
cms_path = 'cms/'
addr = ''
port = 8000

def usage():
    msg("ERROR!")
    exit(1)

settings = {}
util.read_config(settings, settings_file, True)
use_cache = settings.get('use_cache', True)

all_paths = []
input_format = {}
use_db = False
omop = None
if settings.get('omop_use_db', False):
    use_db = True
    omop = OMOP(settings)
else:
    util.convert_paths([ cms_path ], all_paths)

    util.read_format(format_file, input_format, usage)
    cms_analyze.input_format = input_format
    cms_get_patient.input_format = input_format

    build_dictionary.debugOutput = True
    build_dictionary.init(settings, settings_file)

patients_list = 'patients.txt'
json_dir = 'json/'
dictionary_file = os.path.join(json_dir, 'dictionary.json')

patients = set()
def save_patients():
    if not use_cache:
        return
    with open(patients_list, 'w') as pf:
        pf.write('\n'.join(sorted(list(patients))))
        pf.flush()

if not os.path.isfile(patients_list) or not use_cache:
    if use_db:
        omop.list_patients(patients, prefix=json_dir, limit=max_num)
    else:
        tf = StringIO()
        cms_analyze.compute(all_paths, {}, False, tf, filter_zero=True)
        tf.flush()
        tf.seek(0)
        lines = tf.readlines()[-max_num:] if max_num is not None else tf.readlines()
        for line in lines:
            patients.add(json_dir + line.strip() + '.json')
    save_patients()

dict = {}
if os.path.isfile(dictionary_file) and use_cache:
    with open(dictionary_file, 'r') as input:
        dict = json.loads(input.read())

server = create_server((addr, port))
server.bind_path('/', '..')

prefix = '/' + os.path.basename(os.path.normpath(server.base_path))

server.add_default_white_list()
server.add_file_patterns([
        prefix + '/' + json_dir + '*',
        prefix + '/' + patients_list
    ], True)
server.favicon_fallback = 'favicon.ico'

@server.text_get(prefix + '/' + patients_list, 0)
def get_list(req, args):
    return '\n'.join(sorted(list(patients)))

@server.json_get(prefix + '/' + json_dir, 1)
def get_patient(req, args):
    pid = args['paths'][0]
    cache_file = os.path.join(json_dir, pid)
    p_name = json_dir + pid.strip()
    if p_name not in patients:
        patients.add(p_name)
        save_patients()
    if pid.endswith('.json'):
        pid = pid[:-len('.json')]
    if not os.path.isfile(cache_file) or not use_cache:
        if use_db:
            patient = omop.get_patient(pid, dict, line_file, class_file)
        else:
            patient = cms_get_patient.process(all_paths, line_file, class_file, pid)
            build_dictionary.extractEntries(dict, patient)
        if use_cache:
            with open(cache_file, 'w') as pf:
                pf.write(json_dumps(patient))
                pf.flush()
        if use_cache:
            with open(dictionary_file, 'w') as output:
                output.write(json_dumps(dict))
                output.flush()
        return patient
    with open(cache_file, 'r') as pf:
        return json.loads(pf.read())

@server.json_get(prefix + '/' + dictionary_file)
def get_dictionary(req, args):
    return dict

msg("starting server at {0}:{1}", addr if addr else 'localhost', port)
server.serve_forever()
msg("shutting down..")
server.server_close()
