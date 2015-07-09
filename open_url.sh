#!/usr/bin/env bash
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-17 14:26

base_dir=`pwd`
server_pid_file="${base_dir}/server_pid.txt"

USAGE="Usage: $0 -hqc [--no-open] [--] <url>"

usage() {
    echo $USAGE
    echo "-h: print help"
    echo "-q: be quiet"
    echo "-c: check whether the server is running"
    echo "--no-open: only prints the URL"
    echo "<url>: the URL to open"
    exit 1
}

url=
no_open=
quiet=
check_server=
if [ $# -eq 0 ]; then
  usage
fi
while [ $# -gt 0 ]; do
  if [ ! -z "${url}" ]; then
    echo "too many arguments: $@"
    usage
  fi
  case "$1" in
  -h)
    usage
    ;;
  -q)
    quiet=1
    ;;
  -c)
    check_server=1
    ;;
  --no-open)
    no_open=1
    ;;
  --)
    shift
    url="$1"
    ;;
  *)
    url="$1"
    ;;
  esac
  shift
done
if [[ $# -gt 1 ]]; then
  echo "illegal option -- $1"
  usage
fi

if [[ -z "${url}" ]]; then
  echo "require URL"
  usage
fi

print() {
  if [ -z "${quiet}" ]; then
    echo "$@"
  fi
}

if [[ ! -z "${check_server}" && ! -s "${server_pid_file}" && ! -f "${server_pid_file}" ]]; then
  echo "No server running..."
  exit 1
fi

if [ ! -z $no_open ]; then
  echo "${url}"
else
  mac_chrome="/Applications/Google Chrome.app"
  mac_firefox="/Applications/Firefox.app"
  if [ `command -v firefox 2>/dev/null 1>&2; echo $?` -eq 0 ]; then
    # linux firefox
    if [[ -z `ps | grep [f]irefox` ]]; then
      print "open window: ${url}"
      firefox -new-window "${url}" &
    else
      print "open url: ${url}"
      firefox -remote "openURL(${url})" &
    fi
  elif [ `command -v google-chrome 2>/dev/null 1>&2; echo $?` -eq 0 ]; then
    # linux chrome
    print "open window: ${url}"
    google-chrome "${url}"
  elif [ `ls "${mac_chrome}" 2>/dev/null 1>&2; echo $?` -eq 0 ]; then
    # mac chrome
    print "open window: ${url}"
    open "${mac_chrome}" "${url}"
  elif [ `ls "${mac_firefox}" 2>/dev/null 1>&2; echo $?` -eq 0 ]; then
    # mac firefox
    print "open window: ${url}"
    open "${mac_firefox}" "${url}"
  else
    echo "Could not find chrome or firefox..."
    echo "${url}"
    exit 1
  fi
fi
