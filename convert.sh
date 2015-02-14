#!/bin/sh

for id in `./opd_analyze.py -m opd | tail -n 10`
do
  ./opd_get_patient.py -p $id -o "${id}.json" -- opd
done

ls -A *.json > patients.txt
