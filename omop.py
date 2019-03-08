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
    "F": "F",
    "MALE":"M",
    "FEMALE":"F"
}

color_map = {
    "Condition": "#4daf4a",
    "Drug": "#eb9adb",
    "Measurement": "#80b1d3",
    "Observation": "#ccffff",
    "Procedure": "#ff7f00"
}
measure_flag_map = {
    "L": {
        "color": "#fb8072"
    },
    "H": {
        "color": "#fb8072"
    }
}

from StringIO import StringIO

import util

class OMOP():
    def __init__(self, settings, debug_output):
        username = settings['omop_user']
        password = settings['omop_passwd']
        host = settings['omop_host']
        port = settings['omop_port']
        database = settings['omop_db']
        engine = settings.get('omop_engine', 'postgresql')
        self._parents = {}
        self._codes = {}
        if settings['omop_use_alt_hierarchies']:
            if 'ccs_diag' in settings:
                self._codes['Condition_ICD9CM'] = {}
                self._parents['Condition_ICD9CM'] = util.read_CCS(util.get_file(settings['ccs_diag'], debug_output), self._codes['Condition_ICD9CM'])
            if 'ccs_proc' in settings:
                self._codes['Procedure_ICD9CM'] = {}
                self._parents['Procedure_ICD9CM'] = util.read_CCS(util.get_file(settings['ccs_proc'], debug_output), self._codes['Procedure_ICD9CM'])
        self.schema = settings['omop_schema']
        self.db = sqlalchemy.create_engine('{0}://{1}:{2}@{3}:{4}/{5}'.format(engine, username, password, host, port, database))

    def _exec(self, query, **args):
        connection = None
        try:
            connection = self.db.connect()
            q = query.format(schema=self.schema)
            # DEBUG!
            qq = q
            for k in args.keys():
                qq = qq.replace(':'+str(k), "'" + str(args[k]) + "'")
            qq = qq + ';'
            print("{0}".format(qq))
            # DEBUG! END
            return connection.execute(sqlalchemy.text(q), **args)
        finally:
            if connection is not None:
                connection.close()

    def _exec_one(self, query, **args):
        result = self._exec(query, **args)
        res = None
        for r in result:
            if res is not None:
                raise ValueError("expected one result row got more\n{0}\n".format(query))
            res = r
        if res is None:
            raise ValueError("expected one result row got 0\n{0}\n".format(query))
        return res

    def list_patients(self, patients, prefix="", limit=None, show_old_ids=False):
        limit_str = " LIMIT :limit" if limit is not None else ""
        query = "SELECT person_id, person_source_value FROM {schema}.person{limit}".format(schema=self.schema, limit=limit_str)
        for r in self._exec(query, limit=limit):
            patients.add(str(prefix) + (str(r['person_id']) if not show_old_ids else str(r['person_source_value']) + '.json'))

    def get_person_id(self, pid):
        query = "SELECT person_id FROM {schema}.person WHERE person_source_value = :pid"
        return str(self._exec_one(query, pid=pid)['person_id'])

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
        query = """SELECT
             concept_name as gender_concept_name,
             person_source_value,
             year_of_birth
            FROM
             {schema}.person
            LEFT JOIN {schema}.concept ON (
             gender_concept_id = concept_id
            ) WHERE
             person_id = :pid
        """
        result = self._exec_one(query, pid=str(pid))
        if result['person_source_value']:
            self.add_info(obj, 'id_alt', 'ID', str(result['person_source_value']) + ".json")
        self.add_info(obj, 'born', 'Born', int(result['year_of_birth']))
        gender = str(result['gender_concept_name'])
        # defaults to 'U' for "unknown"
        self.add_info(obj, 'gender', 'Gender', gender_map.get(gender.upper(), 'U'), True, gender_label.get(gender, 'U'))

    def to_time(self, value):
        return util.toTime(value.strftime("%Y%m%d"))

    def create_event(self, group, id, claim_id, has_result=False, result_flag="", result=""):
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

    def add_dict(self, dict, new_dict_entries, group, prefix, id, name, desc, code, unmapped):
        alt_hierarchies = str(group) + '_' + str(prefix)
        if group not in dict:
            dict[group] = {}
            dict[group][""] = {
                "id": "",
                "name": group,
                "desc": group,
                "color": color_map.get(group, "lightgray"),
                "parent": ""
            }
            if alt_hierarchies in self._codes:
                ah = {}
                if alt_hierarchies in self._parents:
                    ah = self._parents[alt_hierarchies]
                for (key, value) in self._codes[alt_hierarchies].items():
                    dict[group][key] = {
                        "id": key,
                        "name": value,
                        "desc": value,
                        "los": 0,
                        "parent": ah.get(key, "")
                    }
            if group == "Measurement":
                dict[group][""]["flags"] = measure_flag_map
        g = dict[group]
        full_id = str(prefix) + str(id)
        if full_id not in g:
            res = {
                "id": id,
                "name": name,
                "desc": desc,
                "parent": ""
            }
            if unmapped:
                res["unmapped"] = True
            g[full_id] = res
            do_add = True
            if alt_hierarchies in self._parents:
                print("AH: {0}".format(alt_hierarchies), file=sys.stderr)
                ah = self._parents[alt_hierarchies]
                print("code: {0}".format(code), file=sys.stderr)
                if code in ah:
                    print("true", file=sys.stderr)
                    res["los"] = 0
                    res["parent"] = ah[code]
                    do_add = False
                else:
                    code = code.replace('.', '')
                    print("code: {0}".format(code), file=sys.stderr)
                    if code in ah:
                        print("true fb", file=sys.stderr)
                        res["parent"] = ah[code]
                        do_add = False
            if id != 0 and do_add:
                new_dict_entries.add(str(id))

    def get_dict_entry(self, dict, group, prefix, id):
        if group not in dict:
            return None
        full_id = str(prefix) + str(id)
        return dict[group].get(full_id, None)

    def update_hierarchies(self, dict, new_dict_entries):
        while new_dict_entries:
            query = """SELECT
                 c.concept_id as c_id,
                 c.domain_id as c_domain,
                 c.concept_name as c_name,
                 c.vocabulary_id as c_vocab,
                 c.concept_code as c_num,
                 ca.min_levels_of_separation as c_distance,
                 ca.descendant_concept_id as c_desc_id,
                 cc.domain_id as c_desc_domain,
                 cc.vocabulary_id as c_desc_vocab
                FROM
                 {schema}.concept_ancestor as ca
                LEFT JOIN {schema}.concept as c ON (
                 c.concept_id = ca.ancestor_concept_id
                ) LEFT JOIN {schema}.concept as cc ON (
                 cc.concept_id = ca.descendant_concept_id
                ) WHERE
                 ca.descendant_concept_id != 0
                 AND ca.ancestor_concept_id != 0
                 AND ca.descendant_concept_id IN ( {id_list} )
            """.format(schema=self.schema, id_list=','.join(sorted(list(new_dict_entries))))
            result = self._exec(query)
            new_dict_entries.clear()
            for row in result:
                parent_id = str(row['c_id'])
                parent_group = row['c_domain']
                parent_name = row['c_name']
                parent_vocab = row['c_vocab']
                parent_code = row['c_num']
                unmapped = False
                if parent_code == 0:
                    parent_code = row['c_orig']
                    unmapped = True
                parent_desc = "{0} ({1} {2})".format(parent_name, parent_vocab, parent_code)
                self.add_dict(dict, new_dict_entries, parent_group, parent_vocab, parent_id, parent_name, parent_desc, parent_code, unmapped)
                dos = int(row['c_distance'])
                desc_id = str(row['c_desc_id'])
                desc_vocab = row['c_desc_vocab']
                desc_group = row['c_desc_domain']
                if desc_group != parent_group:
                    print("WARNING: intra group inheritance: {0} << {1}".format(parent_group, desc_group), file=sys.stderr)
                else:
                    desc_entry = self.get_dict_entry(dict, desc_group, desc_vocab, desc_id)
                    if desc_entry is not None and parent_id != desc_id and ('dos' not in desc_entry or desc_entry['dos'] > dos):
                        desc_entry['dos'] = dos
                        desc_entry['parent'] = str(parent_vocab) + str(parent_id)
            new_dict_entries.clear() # we covered everything already (because the table is the full matrix)

    def get_diagnoses(self, pid, obj, dict, new_dict_entries):
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
            {schema}.condition_occurrence as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.condition_concept_id
           )
           WHERE
            o.person_id = :pid
        """
        for row in self._exec(query, pid=pid):
            code = row['d_num']
            unmapped = False
            if code == 0:
                code = row['d_orig']
                unmapped = True
            id_row = 'c' + str(row['id_row'])
            d_id = row['d_id']
            name = row['d_name']
            vocab = row['d_vocab']
            group = "Condition" if row['d_domain'] is None else row['d_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            date_start = self.to_time(row['date_start'])
            date_end = self.to_time(row['date_end']) if row['date_end'] else date_start
            date_cur = date_start
            while date_cur <= date_end:
                event = self.create_event(group, str(vocab) + str(d_id), id_row)
                event['time'] = date_cur
                obj['events'].append(event)
                date_cur = util.nextDay(date_cur)

    def get_procedures(self, pid, obj, dict, new_dict_entries):
        query = """SELECT
            o.procedure_occurrence_id as id_row,
            o.procedure_date as p_date,
            o.procedure_concept_id as p_id,
            o.procedure_source_value as p_orig,
            c.domain_id as p_domain,
            c.concept_name as p_name,
            c.vocabulary_id as p_vocab,
            c.concept_code as p_num
           FROM
            {schema}.procedure_occurrence as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.procedure_concept_id
           )
           WHERE
            o.person_id = :pid
        """
        for row in self._exec(query, pid=pid):
            code = row['p_num']
            unmapped = False
            if code == 0:
                code = row['p_orig']
                unmapped = True
            id_row = 'p' + str(row['id_row'])
            d_id = row['p_id']
            name = row['p_name']
            vocab = row['p_vocab']
            group = "Procedure" if row['p_domain'] is None else row['p_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            event = self.create_event(group, str(vocab) + str(d_id), id_row)
            event['time'] = self.to_time(row['p_date'])
            # if 'p_cost' in row and row['p_cost']:
            #     event['cost'] = float(row['p_cost'])
            obj['events'].append(event)

    def get_observations_concept_valued(self, pid, obj, dict, new_dict_entries):
        query = """SELECT
            o.observation_id as id_row,
            o.observation_date as o_date,
            o.observation_concept_id as o_id,
            o.observation_source_value as o_orig,
            o.value_as_concept_id as o_val_concept,
            c_val.concept_name as o_val_concept_name,
            c.domain_id as o_domain,
            c.concept_name as o_name,
            c.vocabulary_id as o_vocab,
            c.concept_code as o_num
           FROM
            {schema}.observation as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.observation_concept_id
           )
           INNER JOIN {schema}.concept as c_val ON (
	        c_val.concept_id = o.value_as_concept_id
	       )
           WHERE
            o.person_id = :pid
            AND o.value_as_concept_id IS NOT NULL
        """
        for row in self._exec(query, pid=pid):
            code = row['o_num']
            unmapped = False
            if code == 0:
                code = row['o_orig']
                unmapped = True
            id_row = 'p' + str(row['id_row'])
            d_id = row['o_id']
            name = "unknown" if row['o_name'] is None else row['o_name']
            vocab = row['o_vocab']
            group  = "Observation" if row['o_domain'] is None else row['o_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            event = self.create_event(group, str(vocab) + str(d_id), id_row, True, "C",str(row['o_val_concept_name']))
            event['time'] = self.to_time(row['o_date'])
            obj['events'].append(event)

    def get_observations_string_valued(self, pid, obj, dict, new_dict_entries):
        query = """SELECT
            o.observation_id as id_row,
            o.observation_date as o_date,
            o.observation_concept_id as o_id,
            o.observation_source_value as o_orig,
            o.value_as_string  as o_val_string,
            c.domain_id as o_domain,
            c.concept_name as o_name,
            c.vocabulary_id as o_vocab,
            c.concept_code as o_num
           FROM
            {schema}.observation as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.observation_concept_id
           )
           WHERE
            o.person_id = :pid
            AND o.value_as_string IS NOT NULL
        """
        for row in self._exec(query, pid=pid):
            code = row['o_num']
            unmapped = False
            if code == 0:
                code = row['o_orig']
                unmapped = True
            id_row = 'p' + str(row['id_row'])
            d_id = row['o_id']
            name = "unknown" if row['o_name'] is None else row['o_name']
            vocab = row['o_vocab']
            group  = "Observation" if row['o_domain'] is None else row['o_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            event = self.create_event(group, str(vocab) + str(d_id), id_row, True, "S", row['o_val_string'])
            event['time'] = self.to_time(row['o_date'])
            obj['events'].append(event)

    def get_observations_number_valued(self, pid, obj, dict, new_dict_entries):
        query = """SELECT
            o.observation_id as id_row,
            o.observation_date as o_date,
            o.observation_concept_id as o_id,
            o.observation_source_value as o_orig,
            o.value_as_number as o_val_number,
            c.domain_id as o_domain,
            c.concept_name as o_name,
            c.vocabulary_id as o_vocab,
            c.concept_code as o_num
           FROM
            {schema}.observation as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.observation_concept_id
           )
           WHERE
            o.person_id = :pid
            AND o.value_as_number IS NOT NULL
        """
        for row in self._exec(query, pid=pid):
            code = row['o_num']
            unmapped = False
            if code == 0:
                code = row['o_orig']
                unmapped = True
            id_row = 'p' + str(row['id_row'])
            d_id = row['o_id']
            name = "unknown" if row['o_name'] is None else row['o_name']
            vocab = row['o_vocab']
            group  = "Observation" if row['o_domain'] is None else row['o_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            event = self.create_event(group, str(vocab) + str(d_id), id_row, True, "N",str(row['o_val_number']))
            event['time'] = self.to_time(row['o_date'])
            obj['events'].append(event)

    def get_drugs(self, pid, obj, dict, new_dict_entries):
        query = """SELECT
            o.drug_exposure_id as id_row,
            o.drug_exposure_start_date as date_start,
            o.drug_exposure_end_date as date_end,
            o.drug_concept_id as m_id,
            o.drug_source_value as m_orig,
            c.domain_id as m_domain,
            c.concept_name as m_name,
            c.vocabulary_id as m_vocab,
            c.concept_code as m_num
           FROM
            {schema}.drug_exposure as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.drug_concept_id
           )
           WHERE
            o.person_id = :pid
        """
        for row in self._exec(query, pid=pid):
            code = row['m_num']
            unmapped = False
            if code == 0:
                code = row['m_orig']
                unmapped = True
            id_row = 'm' + str(row['id_row'])
            d_id = row['m_id']
            name = row['m_name']
            vocab = row['m_vocab']
            group = "Drug" if row['m_domain'] is None else row['m_domain']
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            date_start = self.to_time(row['date_start'])
            date_end = self.to_time(row['date_end']) if row['date_end'] else date_start
            date_cur = date_start
            # cost = row['m_cost'] if 'm_cost' in row else None
            while date_cur <= date_end:
                event = self.create_event(group, str(vocab) + str(d_id), id_row)
                event['time'] = date_cur
                # if cost:
                #     event['cost'] = float(cost)
                #     cost = None
                obj['events'].append(event)
                date_cur = util.nextDay(date_cur)

    def get_measurements(self, pid, obj, dict, new_dict_entries):
        query = """SELECT
            o.measurement_id as id_row,
            o.measurement_date as m_date,
            o.measurement_concept_id as m_id,
            o.measurement_source_value as m_orig,
            o.value_source_value as m_orig_value,
            o.value_as_number as m_value,
            o.range_low as m_low,
            o.range_high as m_high,
            c.domain_id as m_domain,
            c.concept_name as m_name,
            c.vocabulary_id as m_vocab,
            c.concept_code as m_num
           FROM
            {schema}.measurement as o
           LEFT JOIN {schema}.concept as c ON (
            c.concept_id = o.measurement_concept_id
           )
           WHERE
            o.person_id = :pid
        """
        for row in self._exec(query, pid=pid):
            code = row['m_num']
            unmapped = False
            if code == 0:
                code = row['m_orig']
                unmapped = True
            id_row = 'l' + str(row['id_row'])
            d_id = row['m_id']
            name = row['m_name']
            vocab = row['m_vocab']
            group = "Measurement" if row['m_domain'] is None else row['m_domain']
            lab_value = float(row['m_value']) if 'm_value' in row and row['m_value'] else row['m_orig_value']
            lab_low = float(row['m_low'] if row['m_low'] is not None else '-inf')
            lab_high = float(row['m_high'] if row['m_high'] is not None else 'inf')
            lab_flag = ""
            if lab_value is not None:
                if lab_value <= lab_low:
                    lab_flag = "L"
                elif lab_value >= lab_high:
                    lab_flag = "H"
            else:
                lab_value = "n/a"
            desc = "{0} ({1} {2})".format(name, vocab, code)
            self.add_dict(dict, new_dict_entries, group, vocab, d_id, name, desc, code, unmapped)
            event = self.create_event(group, str(vocab) + str(d_id), id_row, True, lab_flag, str(lab_value))
            event['time'] = self.to_time(row['m_date'])
            obj['events'].append(event)

    def get_visits(self, pid, obj):
        classes = obj["classes"]
        query = """SELECT
             v.visit_start_date as date_start,
             v.visit_end_date as date_end,
             c.concept_name as c_name
            FROM
             {schema}.visit_occurrence as v
            LEFT JOIN {schema}.concept as c ON (
             v.visit_concept_id = c.concept_id
            ) WHERE
             v.person_id = :pid
             AND c.concept_name IN ( {classes} )
        """.format(schema=self.schema, classes=','.join(sorted([ "'{0}'".format(k) for k in classes.keys()])))
        v_spans = obj["v_spans"]
        for row in self._exec(query, pid=pid):
            visit_name = str(row['c_name'])
            date_start = self.to_time(row['date_start'])
            date_end = self.to_time(row['date_end'])
            v_spans.append({
                "class": visit_name,
                "from": date_start,
                "to": date_end
            })

    def get_patient(self, pid, dictionary, line_file, class_file):
        obj = {
            "info": [],
            "events": [],
            "h_bars": [],
            "v_bars": [ "auto" ],
            "v_spans": [],
            "classes": {}
        }
        new_dict_entries = set()
        util.add_files(obj, line_file, class_file)
        self.get_info(pid, obj)
        self.add_info(obj, "pid", "Patient", pid)
        self.get_info(pid, obj)
        self.get_diagnoses(pid, obj, dictionary, new_dict_entries)
        self.get_observations_concept_valued(pid, obj, dictionary, new_dict_entries)
        self.get_observations_string_valued(pid, obj, dictionary, new_dict_entries)
        self.get_observations_number_valued(pid, obj, dictionary, new_dict_entries)
        self.get_procedures(pid, obj, dictionary, new_dict_entries)
        self.get_drugs(pid, obj, dictionary, new_dict_entries)
        self.get_measurements(pid, obj, dictionary, new_dict_entries)
        self.get_visits(pid, obj)
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
        self.update_hierarchies(dictionary, new_dict_entries)
        return obj
