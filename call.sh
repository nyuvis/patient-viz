#!/bin/bash
root=`dirname "$0"`
venv="${root}/.venv"
venv_activate="${venv}/bin/activate"

if [ -d "${venv}" ]; then
  source ${venv_activate}
fi
if [ ! -z "${TEST_DEBUG}" ]; then
  # We cannot use set -o xtrace to print the command
  # because stderr needs to be forwarded. Instead we
  # print the command to a new file descriptor which
  # needs to be set up manually. Debugging is set up
  # in the parent script like this:
  #
  # exec 3>&2
  # export TEST_DEBUG="TEST_DEBUG"
  #
  echo "$@" >&3
fi
python "$@"
