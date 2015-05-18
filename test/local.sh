#!/bin/bash
# @author Joschi <josua.krause@gmail.com>
# created 2015-05-13 11:11

cd "$(dirname $0)"

exec 3>&2
export TEST_DEBUG="TEST_DEBUG"

CMS_DIR="../cms"
OUTPUT="./output"
FEATURE_EXTRACT="../feature_extraction"

cohort="./etc/cohort.txt"
format="../format.json"
config="../config.txt"

print() {
  echo "$@" 2>&1
}

check() {
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

print "test: training predictive model"

if [ ! -f "${cohort}" ]; then
  print "building cohort"
  ${FEATURE_EXTRACT}/cohort.py --debug --query-file "${FEATURE_EXTRACT}/cases.txt" -f "${format}" -c "${config}" -o "${OUTPUT}/cohort_cases.txt.tmp_local" -- "$CMS_DIR"
  ${FEATURE_EXTRACT}/cohort.py --debug --query-file "${FEATURE_EXTRACT}/control.txt" -f "${format}" -c "${config}" -o "${OUTPUT}/cohort_control.txt.tmp_local" -- "$CMS_DIR"
  ${FEATURE_EXTRACT}/merge.py --cases "${OUTPUT}/cohort_cases.txt.tmp_local" --control "${OUTPUT}/cohort_control.txt.tmp_local" -o "${cohort}" --test 30 --seed 0
else
  print "use existing cohort at ${cohort}"
fi

${FEATURE_EXTRACT}/extract.py --debug -w "${cohort}" --age-time 20100101 --to 20100101 -o - -f "${format}" -c "${config}" -- "$CMS_DIR" | \
${FEATURE_EXTRACT}/train.py -w --in - --out "${OUTPUT}/model" --seed 0 --model reg -v 20 2> "${OUTPUT}/train.txt.tmp_local"
check $?
check_file "${OUTPUT}/train.txt" "${OUTPUT}/train.txt.tmp_local"

rm -- ${OUTPUT}/*.tmp_local
rm -r -- ${OUTPUT}/model/

print "all tests successful!"
exec 3>&- # don't really need to close the FD
exit 0
