# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@";" """
import os
import sys
import json

sys.path.append('lib')

from quick_server.quick_server import create_server, msg

patients_list = 'patients.txt'
dictionary_file = 'dictionary.json'
json_dir = 'json/'

addr = ''
port = 8000
server = create_server((addr, port))
server.bind_path('/', '..')
server.add_default_white_list()
server.favicon_fallback = 'favicon.ico'

prefix = '/' + os.path.basename(os.path.normpath(server.base_path))

@server.text_get(prefix + '/' + patients_list)
def get_list(req, args):
    with open(patients_list) as pf:
        return pf.read()

@server.json_get(prefix + '/' + json_dir, 1)
def get_patient(req, args):
    with open(os.path.join(json_dir, args['paths'][0])) as pf:
        return json.loads(pf.read())

@server.json_get(prefix + '/' + json_dir + dictionary_file)
def get_dictionary(req, args):
    with open(os.path.join(json_dir, dictionary_file)) as pf:
        return json.loads(pf.read())

msg("starting server at {0}:{1}", addr if addr else 'localhost', port)
server.serve_forever()
msg("shutting down..")
server.server_close()
