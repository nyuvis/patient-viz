#!/usr/bin/env bash
# @author Joschi <josua.krause@gmail.com>
# created 2015-04-26 23:11

cd "$(dirname $0)"

exec 3>&2
export TEST_DEBUG=3

CMS_DIR="./cms"
ERR_FILE="err.txt"
OUTPUT="./output"
FEATURE_EXTRACT="../feature_extraction"

format="../format.json"
style_classes="../style_classes.json"
etc="./etc"
config="${etc}/config.txt.tmp"
config_regr="${etc}/config.txt"

print() {
  echo "$@" 2>&1
}

check() {
  if [ -s $ERR_FILE ]; then
    cat $ERR_FILE
    print "^ error file not empty ^"
    exit 1
  fi
  if [ $1 -ne 0 ]; then
    print "^ command failed ^"
    exit 2
  fi
}

check_file() {
  diff -q "$1" "$2"
  if [ $? -ne 0 ]; then
    diff -u "$1" "$2"
    print "^ $1 doesn't match $2 ^"
    exit 3
  fi
}

convert_patient() {
  print "test: convert patient"
  rm -- "${OUTPUT}/${id}.json.tmp" 2> /dev/null
  rm -- "${OUTPUT}/dictionary.json.tmp" 2> /dev/null
  id=$1
  ../cms_get_patient.py -p "${id}" -f "${format}" -o "${OUTPUT}/${id}.json.tmp" -c "${style_classes}" -- "${CMS_DIR}" 2> $ERR_FILE
  check $?
  check_file "${OUTPUT}/${id}.json" "${OUTPUT}/${id}.json.tmp"
  ../build_dictionary.py --debug -p "${OUTPUT}/${id}.json.tmp" -c "${config}" -o "${OUTPUT}/dictionary.json.tmp"
  check $?
  check_file "${OUTPUT}/dictionary.json" "${OUTPUT}/dictionary.json.tmp"
  check_file "${config_regr}" "${config}"
}

create_predictive_model() {
  print "test: create predictive model"
  rm -- "${OUTPUT}/cohort_cases.txt.tmp" 2> /dev/null
  rm -- "${OUTPUT}/cohort_control.txt.tmp" 2> /dev/null
  rm -- "${OUTPUT}/cohort.txt.tmp" 2> /dev/null
  rm -- "${OUTPUT}/output.csv.tmp" 2> /dev/null
  rm -- "${OUTPUT}/headers.json.tmp" 2> /dev/null
  ${FEATURE_EXTRACT}/cohort.py --debug --query-file "${etc}/cases.txt" -f "${format}" -c "${config}" -o "${OUTPUT}/cohort_cases.txt.tmp" -- "${CMS_DIR}"
  check $?
  check_file "${OUTPUT}/cohort_cases.txt" "${OUTPUT}/cohort_cases.txt.tmp"
  check_file "${config_regr}" "${config}"
  ${FEATURE_EXTRACT}/cohort.py --debug --query-file "${etc}/control.txt" -f "${format}" -c "${config}" -o "${OUTPUT}/cohort_control.txt.tmp" -- "${CMS_DIR}"
  check $?
  check_file "${OUTPUT}/cohort_control.txt" "${OUTPUT}/cohort_control.txt.tmp"
  check_file "${config_regr}" "${config}"
  ${FEATURE_EXTRACT}/merge.py --cases "${OUTPUT}/cohort_cases.txt.tmp" --control "${OUTPUT}/cohort_control.txt.tmp" -o "${OUTPUT}/cohort.txt.tmp" --test 30 --seed 0 2> $ERR_FILE
  check $?
  check_file "${OUTPUT}/cohort.txt" "${OUTPUT}/cohort.txt.tmp"
  ${FEATURE_EXTRACT}/extract.py --debug -w "${OUTPUT}/cohort.txt.tmp" --num-cutoff 0 --age-time 20100101 --to 20100101 -o "${OUTPUT}/output.csv.tmp" -f "${format}" -c "${config}" -- "${CMS_DIR}"
  check $?
  check_file "${OUTPUT}/output.csv" "${OUTPUT}/output.csv.tmp"
  check_file "${config_regr}" "${config}"
  head -n 1 "${OUTPUT}/output.csv.tmp" | sed "s/,/ /g" | ../build_dictionary.py --debug -o "${OUTPUT}/headers.json.tmp" -c "${config}" --lookup -
  check $?
  check_file "${OUTPUT}/headers.json" "${OUTPUT}/headers.json.tmp"
  check_file "${config_regr}" "${config}"
}

cp "${config_regr}" "${config}"

convert_patient "8CDC0C5ACBDFC9CE"
create_predictive_model

rm -- "${ERR_FILE}" "${config}" ${OUTPUT}/*.tmp

print "all tests successful!"
exec 3>&- # don't really need to close the FD
exit 0
