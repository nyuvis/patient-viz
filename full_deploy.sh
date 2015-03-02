#!/bin/sh
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-27 10:39

master="master"
web="gh-pages"
origin="origin"

USAGE="Usage: $0 -h [--full]"

usage() {
    echo $USAGE
    echo "-h: print help"
    echo "--full: whether to update the patient files"
    exit 1
}

full=
while [ $# -gt 0 ]; do
  case "$1" in
  -h)
    usage ;;
  --full)
    full=1
    ;;
  *)
    echo "illegal option -- $1"
    usage ;;
  esac
  shift
done
if [[ $# -gt 1 ]]; then
  echo "illegal option -- $1"
  usage
fi

test_fail() {
  if [ $1 -ne 0 ]; then
    echo "deploying failed!"
    exit 1
  fi
}

prompt() {
  abort=
  text=$1
  while true; do
    read -p "${text} [y]es [n]o: " yn
    case $yn in
      [Yy]* )
        break
        ;;
      [Nn]* )
        abort=1
        break
        ;;
    esac
  done

  if [ ! -z "${abort}" ]; then
    return 1
  fi
  return 0
}

msg="Do you really want to publish to ${origin}/${web}"
if [ ! -z "${full}" ]; then
  msg="${msg} and update patient files"
fi
prompt "${msg}?"
if [ $? -ne 0 ]; then
  exit 0
fi

if [ -z "${full}" ] && [ -z `git branch -r --no-merged "${web}" | grep "${master}"` ]; then
  echo "gh-pages already up to date"
  exit 1
fi

onmaster=`git branch | grep "* ${master}"`
if [ -z "${onmaster}" ]; then
  echo "not on ${master}"
  exit 1
fi

echo "save current patient files"
zip "json.zip" "patients.txt" "json/"
test_fail $?

git checkout "${web}" && git merge --no-ff "${master}" --no-commit
test_fail $?

if [ ! -z "${full}" ]; then
  ./setup.sh --clean --default --convert "9F6F484429DDCC04 AE056C5933AFED18 298C80CC2F7CEDC4 EB704BFBAB4E2B86 B7ECA3897A4AD00D A9BD9D012E87A360 4EF051B883DE5192 998093F33FE2D940 CDBF9E622DEE5B07 AEF023C2029F05BC"
  test_fail $?
  git add -f json/9F6F484429DDCC04.json json/AE056C5933AFED18.json json/298C80CC2F7CEDC4.json json/EB704BFBAB4E2B86.json json/B7ECA3897A4AD00D.json json/A9BD9D012E87A360.json json/4EF051B883DE5192.json json/998093F33FE2D940.json json/CDBF9E622DEE5B07.json json/AEF023C2029F05BC.json json/dictionary.json patients.txt
  test_fail $?
fi

git commit
test_fail $?

git push "${origin}" "${web}" && git checkout "${master}"
test_fail $?

echo "restore patient files"
if [ -d "json" ]; then
  rm -r "json"
fi
unzip "json.zip"
