# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/call.sh" "$0" "$@";" """
from __future__ import print_function

import os
import sys
import json
import sqlalchemy

gender_label = {
    "M": "primary",
    "W": "danger",
    "F": "danger"
}
gender_map = {
    "M": "M",
    "W": "F",
    "F": "F"
}

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

    def _exec(self, query, *args):
        connection = None
        try:
            connection = self.db.connect()
            return connection.execute(query.format(schema=self.schema), *args)
        finally:
            if connection is not None:
                connection.close()

    def _exec_one(self, query, *args):
        result = self._exec(query, *args)
        if len(result) != 1:
            raise ValueError("expected one result row got {0}\n{1}\n".format(len(result), query))
        return result[0]

    def list_patients(self, patients, prefix="", limit=None):
        limit_str = "LIMIT :limit"+limit if limit is not None else ""
        query = "SELECT person_id FROM {schema}.person{limit}".format(limit=limit_str)
        for r in self._exec(query, limit=limit):
            patients.add(prefix = r['person_id'])

    def add_info(self, obj, id, key, value, has_label = False, label = ""):
        for info in obj["info"]:
            if info["id"] == id:
                if str(value) != str(info["value"]):
                    print('duplicate "'+id+'" new: '+str(value)+' old: '+str(info["value"]), file=sys.stderr)
                return
        node = {
            "id": id,
            "name": key,
            "value": value,
        }
        if has_label:
            node["label"] = label
        obj["info"].append(node)

    def get_info(self, pid, obj):
        query = "SELECT year_of_birth, gender_source_value FROM {schema}.person WHERE person_id = :pid"
        result = self._exec_one(query, pid=pid)
        self.add_info(obj, 'born', 'Born', int(result['year_of_birth']))
        gender = str(result['gender_source_value'])
        self.add_info(obj, 'gender', 'Gender', gender_map.get(gender, 'U'), True, gender_label.get(gender, "default"))

    def to_time(self, value):
        return util.toTime(''.join(value.split('-')))

    def create_event(self, group, id, claim_id, has_result=False, result_flag=False, result=""):
        res = {
            "id": id,
            "group": group
        }
        if claim_id is not None:
            res["row_id"] = claim_id
        if has_result:
            res["flag_value"] = result
            res["flag"] = result_flag
        return res

    def add_dict(self, dict, group, prefix, id, name, desc, color, unmapped):
        if group not in dict:
            dict[group] = {}
            dict[group][""] = {
                "id": "",
                "name": group,
                "desc": group,
                "color": color,
                "parent": ""
            }
        g = dict[group]
        full_id = prefix + id
        if full_id not in g:
            res = {
                "id": id,
                "name": name,
                "desc": desc,
                "parent": ""
            }
            if unmapped:
                res["unmapped"] = True
            if g[""]["color"] != color:
                res["color"] = color
            g[full_id] = res

    def get_diagnoses(self, pid, obj, dict):
        query = """SELECT
            o.condition_occurrence_id as id_row,
            o.condition_start_date as date_start,
            o.condition_end_date as date_end,
            o.condition_concept_id as d_id,
            o.condition_source_value as d_orig,
            c.domain_id as d_domain,
            c.concept_name as d_name,
            c.vocabulary_id as d_vocab,
            c.concept_code as d_num
           FROM
            {schema}.condition_occurrence as o,
            {schema}.concept as c
           WHERE
            o.person_id = :pid
            and c.concept_id = o.condition_concept_id
        """
        for row in self._exec(query, pid=pid):
            code = row['d_num']
            unmapped = False
            if code == 0:
                code = row['d_orig']
                unmapped = True
            id_row = row['id_row']
            d_id = row['d_id']
            name = row['d_name']
            vocab = row['d_vocab']
            group = row['d_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, group, vocab, d_id, name, desc, "#4daf4a", unmapped)
            date_start = self.to_time(row['date_start'])
            date_end = self.to_time(row['date_end']) if row['date_end'] else date_start
            date_cur = date_start
            while date_cur <= date_end:
                event = self.create_event(group, vocab + d_id, id_row)
                event['time'] = curDate
                obj['events'].append(event)
                date_cur = util.nextDay(date_cur)

    def get_patient(self, pid, dictionary, line_file, class_file):
        obj = {
            "info": [],
            "events": [],
            "h_bars": [],
            "v_bars": [ "auto" ],
            "v_spans": [],
            "classes": {}
        }
        util.add_files(obj, line_file, class_file)
        self.get_info(pid, obj["info"])
        self.add_info(obj, "pid", "Patient", pid)
        self.get_info(pid, obj)
        self.get_diagnoses(pid, obj, dict)
        min_time = float('inf')
        max_time = float('-inf')
        for e in obj["events"]:
            time = e["time"]
            if time < min_time:
                min_time = time
            if time > max_time:
                max_time = time
        obj["start"] = min_time
        obj["end"] = max_time
        self.add_info(obj, "event_count", "Events", len(obj["events"]))
        return obj
