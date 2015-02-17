#!/bin/sh
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-16 14:00

JSON_DIR="json"
base_dir=`pwd`
dictionary="${JSON_DIR}/dictionary.json"
file_list="patients.txt"
server_pid_file="${base_dir}/server_pid.txt"
server_log="${base_dir}/server_log.txt"
server_err="${base_dir}/server_err.txt"

USAGE="Usage: $0 -hq -p <patient file> [-d <dictionary file>] [--url] [--start|--stop] [--list|--list-update]"

usage() {
    echo $USAGE
    echo "-h: print help"
    echo "-q: be quiet"
    echo "-p <patient file>: the patient file to load"
    echo "-d <dictionary file>: the dictionary file to load"
    echo "--list: lists all available patient files"
    echo "--list-update: updates this list"
    echo "--url: only prints the URL (does not open a browser)"
    echo "--start: starts the server"
    echo "--stop: stops the server"
    exit 1
}

pfile=
dfile="${JSON_DIR}/dictionary.json"
only_url=
do_start=
do_stop=
show_list=
update_list=
quiet=

if [ $# -eq 0 ]; then
  usage
fi
while [ $# -gt 0 ]; do
  case "$1" in
  -h)
    usage
    ;;
  -q)
    quiet="-q"
    ;;
  -p)
    shift
    pfile="$1"
    ;;
  -d)
    shift
    dfile="$1"
    ;;
  --url)
    only_url="--no-open"
    ;;
  --start)
    do_start=1
    ;;
  --stop)
    do_stop=1
    ;;
  --list)
    show_list=1
    ;;
  --list-update)
    update_list=1
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

if [[ -z $pfile && -z $do_start && -z $do_stop && -z $show_list && -z $update_list ]]; then
  echo "require patient file"
  usage
fi

cd_back() {
  cd "${base_dir}"
}

print() {
  if [ -z "${quiet}" ]; then
    echo "$@"
  fi
}

if [ ! -z $do_start ]; then
  if [[ -s "${server_pid_file}" || -f "${server_pid_file}" ]]; then
    print "Server already running..."
  else
    print "Starting server..."
    cd ..
    python -m SimpleHTTPServer > "${server_log}" 2> "${server_err}" &
    server_pid=$!
    echo "${server_pid}" > "${server_pid_file}"
    cd_back
  fi
fi

if [ ! -z $do_stop ]; then
  if [[ -s "${server_pid_file}" || -f "${server_pid_file}" ]]; then
    server_pid=`cat "${server_pid_file}"`
    print "Server pid: ${server_pid}"
    kill "${server_pid}"
    rm -- "${server_pid_file}" 2> /dev/null
  else
    print "No server running..."
  fi
fi

if [ ! -z $update_list ]; then
  find "${JSON_DIR}" -name "*.json" -and -not -path "${dictionary}" > "${file_list}"
fi

if [ ! -z $show_list ]; then
  cat "${file_list}"
fi

if [ -z "${pfile}" ]; then
  exit 0
fi

./open_url.sh -c "${quiet}" "${only_url}" -- "http://localhost:8000/patient-viz/index.html?p=${pfile}&d=${dfile}"
