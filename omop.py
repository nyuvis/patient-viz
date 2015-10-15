# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@";" """
from __future__ import print_function

import os
import sys
import json
import sqlalchemy

from StringIO import StringIO

import util

class OMOP():
  def __init__(self, settings):
    username = settings['omop_user']
    password = settings['omop_passwd']
    host = settings['omop_host']
    port = settings['omop_port']
    database = settings['omop_db']
    self.schema = settings['omop_schema']
    self.db = sqlalchemy.create_engine('postgresql://{0}:{1}@{2}:{3}/{4}'.format(username, password, host, port, database))

  def _exec(self, query):
    connection = None
    try:
      connection = self.db.connect()
      return connection.execute(query.format(schema=self.schema))
    finally:
      if connection is not None:
        connection.close()

  def list_patients(self, patients, prefix="", limit=None):
    limit_str = "LIMIT "+limit if limit is not None else ""
    query = "SELECT person_id FROM {schema}.person{limit};".format(limit=limit_str)
    for r in self._exec(query):
      patients.add(prefix = r['person_id'])

  def get_patient(self, pid, dictionary):
    return {}
