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

sys.path.append('lib')

from quick_server.quick_server import create_server, msg

settings_file = 'config.txt'
format_file = 'format.json'
class_file = 'style_classes.json'
line_file = None
cms_path = 'cms/'

def usage():
    msg("ERROR!")
    exit(1)

all_paths = []
util.convert_paths([ cms_path ], all_paths)

input_format = {}
util.read_format(format_file, input_format, usage)
cms_analyze.input_format = input_format
cms_get_patient.input_format = input_format

settings = {}
util.read_config(settings, settings_file, True)
build_dictionary.debugOutput = True
build_dictionary.init(settings, settings_file)

patients_list = 'patients.txt'
json_dir = 'json/'
dictionary_file = os.path.join(json_dir, 'dictionary.json')

max_num = 100

patients = set()
def save_patients():
    with open(patients_list, 'w') as pf:
        pf.write('\n'.join(sorted(list(patients))))
        pf.flush()

if not os.path.isfile(patients_list):
    tf = StringIO()
    cms_analyze.compute(all_paths, {}, False, tf, filter_zero=True)
    tf.flush()
    tf.seek(0)
    for line in tf.readlines()[-max_num:]:
        patients.add(json_dir + line.strip() + '.json')
    save_patients()

dict = {}
if os.path.isfile(dictionary_file):
    with open(dictionary_file, 'r') as input:
        dict = json.loads(input.read())

addr = ''
port = 8000
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
    if not os.path.isfile(cache_file):
        patient = cms_get_patient.process(all_paths, line_file, class_file, pid)
        with open(cache_file, 'w') as pf:
            pf.write(json.dumps(patient))
            pf.flush()
        build_dictionary.extractEntries(dict, patient)
        with open(dictionary_file, 'w') as output:
            output.write(json.dumps(dict))
            output.flush()
    with open(cache_file, 'r') as pf:
        return json.loads(pf.read())

@server.json_get(prefix + '/' + dictionary_file)
def get_dictionary(req, args):
    return dict

msg("starting server at {0}:{1}", addr if addr else 'localhost', port)
server.serve_forever()
msg("shutting down..")
server.server_close()
