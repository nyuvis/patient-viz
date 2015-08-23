# -*- coding: utf-8 -*-
# -*- mode: python; -*-
"""exec" "`dirname \"$0\"`/../call.sh" "$0" "$@";" """
from __future__ import print_function
from __future__ import division

import time as time_lib
from datetime import datetime, timedelta
import sys
import math
import json
import os
import csv
import re
import numpy as np
from sklearn.manifold import TSNE

sys.path.append('..')

import util

__doc__ = """
Created on 2015-08-23

@author: joschi
"""

def is_number(s):
    try:
        return not math.isnan(float(s))
    except ValueError:
        return False

def get_variables(fin, col_matches, outcome_cols):
    names = None
    header = None
    category = None
    outcomes = None
    out_names = None
    rows = []
    outs = []
    for row in csv.reader(fin):
        if header is None:

            def ok(h):
                if any(c.search(h) is not None for (c, white) in col_matches if not white):
                    return False
                return any(c.search(h) is not None for (c, white) in col_matches if white)

            header = [ ix for (ix, h) in enumerate(row) if ok(h) ]
            names = [ row[ix] for ix in header ]
            category = [ False for _ in header ]
            outcomes = [ ix for (ix, h) in enumerate(row) if h in outcome_cols ]
            out_names = [ row[ix] for ix in outcomes ]
            continue
        ovals = []
        for oix in outcomes:
            ovals.append(row[oix])
        outs.append(ovals)
        vals = []
        for (ix, hix) in enumerate(header):
            val = row[hix]
            if not is_number(val):
                category[ix] = True
            vals.append(val)
        rows.append(vals)
    cat_names = [ names[ix] for (ix, c) in enumerate(category) if c ]
    num_names = [ names[ix] for (ix, c) in enumerate(category) if not c ]
    cats = np.matrix([ [ r[ix] for (ix, c) in enumerate(category) if c ] for r in rows ])
    nums = np.matrix([ [ float(r[ix]) for (ix, c) in enumerate(category) if not c ] for r in rows ])
    return cats, nums, outs, cat_names, num_names, out_names

def compute_dist_matrix(cats, nums, stddevs):
    dist_matrix = np.zeros((nums.shape[0], nums.shape[0]))

    def compute_dist_cat(aix, bix, cat):
        return 1 if cats[aix, cat] == cats[bix, cat] else 0

    def compute_dist_num(aix, bix, num):
        diff = (nums[aix, num] - nums[bix, num]) / stddevs[num] * 0.5;
        return diff * diff;

    def compute_dist(aix, bix):
        res = math.fsum(compute_dist_num(aix, bix, num) for num in xrange(nums.shape[1]))
        return res + math.fsum(compute_dist_cat(aix, bix, cat) for cat in xrange(cats.shape[1]))

    for aix in xrange(nums.shape[0]):
        for bix in xrange(aix):
            d = compute_dist(aix, bix)
            dist_matrix[aix, bix] = d
            dist_matrix[bix, aix] = d
    return dist_matrix

def project(fin, fout, col_matches, outcome_cols):
    seed = 0
    cats, nums, outs, cat_names, num_names, out_names = get_variables(fin, col_matches, outcome_cols)
    means = np.mean(nums, axis=0).tolist()[0]
    stddevs = [ s if s != 0 else 1 for s in np.std(nums, axis=0).tolist()[0] ]
    dist_matrix = compute_dist_matrix(cats, nums, stddevs)
    proj = TSNE(metric="precomputed", random_state=seed)
    points = proj.fit_transform(dist_matrix)
    json.dump({
        'nums': {
            'names': num_names,
            'data': nums.tolist(),
            'means': means,
            'stddevs': stddevs
        },
        'cats': {
            'names': cat_names,
            'data': cats.tolist()
        },
        'outs': {
            'names': out_names,
            'data': outs
        },
        'projection': {
            'points': points.tolist()
        }
    }, fout, sort_keys=True, indent=2)

def usage():
    print("""
usage: {0} [-h] [--in <file>]
-h: print help
--in <file>: specifies the input file. default is '-' which is STD_IN
""".strip().format(sys.argv[0]), file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    input = '-'
    col_matches = [
        (re.compile('^info__'), True),
        (re.compile('HIERARCHY\.[0-9]+$'), True),
        (re.compile('^info__claim_cost$'), False)
    ]
    outcome_cols = set([ 'id', 'info__claim_cost' ])
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '-h':
            usage()
        if arg == '--in':
            if not len(args):
                print('--in requires input file', file=sys.stderr)
                usage()
            input = args.pop(0)
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    with util.OutWrapper('-') as out:
        if input != '-':
            with open(input, 'r') as fin:
                project(fin, out, col_matches, outcome_cols)
        else:
            project(sys.stdin, out, col_matches, outcome_cols)
