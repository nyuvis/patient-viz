#!/bin/bash
# @author Joschi <josua.krause@gmail.com>
# created 2015-04-26 23:11


CMS_DIR="./cms"
ERR_FILE="err.txt"
OUTPUT="./output"
FEATURE_EXTRACT="../feature_extraction"

format="../format.json"
style_classes="../style_classes.json"
etc="./etc"
config="${etc}/config.txt"

check() {
  if [ -s $ERR_FILE ]; then
    cat $ERR_FILE
    echo "^ error file not empty ^"
    exit 1
  fi
  if [ $1 -ne 0 ]; then
    echo "^ command failed ^"
    exit 2
  fi
}

check_file() {
  diff $1 $2
  if [ $? -ne 0 ]; then
    echo "^ $1 doesn't match $2 ^"
    exit 3
  fi
}

convert_patient() {
  id=$1
  ../cms_get_patient.py -p "${id}" -f "${format}" -o "${OUTPUT}/${id}.json.tmp" -c "${style_classes}" -- "${CMS_DIR}" 2> $ERR_FILE
  check $?
  check_file "${OUTPUT}/${id}.json" "${OUTPUT}/${id}.json.tmp"
  ../build_dictionary.py -p "${OUTPUT}/${id}.json.tmp" -c "${config}" -o "${OUTPUT}/dictionary.json.tmp" 2> $ERR_FILE
  check $?
  check_file "${OUTPUT}/dictionary.json" "${OUTPUT}/dictionary.json.tmp"
}

create_predictive_model() {
  ${FEATURE_EXTRACT}/cohort.py --query-file "${etc}/cases.txt" -f "${format}" -c "${config}" -o "${OUTPUT}/cohort_cases.txt.tmp" -- "${CMS_DIR}"
  check $?
  check_file "${OUTPUT}/cohort_cases.txt" "${OUTPUT}/cohort_cases.txt.tmp"
  ${FEATURE_EXTRACT}/cohort.py --query-file "${etc}/control.txt" -f "${format}" -c "${config}" -o "${OUTPUT}/cohort_control.txt.tmp" -- "${CMS_DIR}"
  check $?
  check_file "${OUTPUT}/cohort_control.txt" "${OUTPUT}/cohort_control.txt.tmp"
  ${FEATURE_EXTRACT}/merge.py --cases "${OUTPUT}/cohort_cases.txt.tmp" --control "${OUTPUT}/cohort_control.txt.tmp" -o "${OUTPUT}/cohort.txt.tmp" --test 30 --seed 0 2> $ERR_FILE
  check $?
  check_file "${OUTPUT}/cohort.txt" "${OUTPUT}/cohort.txt.tmp"
  ${FEATURE_EXTRACT}/extract.py -w "${OUTPUT}/cohort.txt.tmp" --num-cutoff 1 --age-time 20100101 --to 20100101 -o "${OUTPUT}/output.csv.tmp" -f "${format}" -c "${config}" -- "${CMS_DIR}"
  check $?
  check_file "${OUTPUT}/output.csv" "${OUTPUT}/output.csv.tmp"
  head -n 1 "${OUTPUT}/output.csv.tmp" | sed "s/,/ /g" | ../build_dictionary.py -o "${OUTPUT}/headers.json.tmp" -c "${config}" --lookup -
  check $?
  check_file "${OUTPUT}/headers.json" "${OUTPUT}/headers.json.tmp"
}

convert_patient "8CDC0C5ACBDFC9CE"
create_predictive_model

rm $ERR_FILE
exit 0
