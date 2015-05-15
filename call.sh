#!/bin/bash
root=`dirname "$0"`
venv="${root}/.venv"
venv_activate="${venv}/bin/activate"

if [ -d "${venv}" ]; then
  source ${venv_activate}
fi
python "$@"
