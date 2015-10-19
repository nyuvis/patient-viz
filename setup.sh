#!/usr/bin/env bash
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-16 09:00

PNT_DIR="code/pnt"
NDC_DIR="code/ndc"
ICD9_DIR="code/icd9"
CCS_DIR="code/ccs"
CMS_DIR="cms"
JSON_DIR="json"
CMS_SAMPLE_ALL=`seq -s " " 1 20`

base_dir=`pwd`
convert_top_n=3
convert_list=
dictionary="${JSON_DIR}/dictionary.json"
config="config.txt"
config_omop="config_omop.txt"
format="format.json"
style_classes="style_classes.json"
err_file="err.txt"
err_dict_file="err_dict.txt"
server_log="server_log.txt"
server_err="server_err.txt"
file_list="patients.txt"
fetch_samples="10"
venv=".venv"
venv_activate="${venv}/bin/activate"

no_prompt=
pn=
ndc=
cms=
icd9=
ccs=
pip=
apt=
psql=
omop=
do_convert=
do_clean=
do_clean_cache=
do_update=
do_nop=
do_burst=
shelve=

USAGE="Usage: $0 -hs [-c <dictionary config file>] [-f <table format file>] [--samples <list of samples>] [--samples-all] [--convert <list of ids>] [--convert-num <top n>] [--default] [--default-omop] [--icd9] [--ccs] [--ndc] [--pnt] [--cms] [--burst] [--do-convert] [--clean] [--clean-cache] [--update] [--pip] [--apt] [--psql] [--omop] [--shelve] [--nop]"

usage() {
    echo $USAGE
    echo "-h: print help"
    echo "-c <dictionary config file>: specify the dictionary config file"
    echo "-f <table format file>: specify the table format file"
    echo "-s: do not prompt the user for input"
    echo "--samples <list of samples>: specify which samples to download (1-20)"
    echo "--samples-all: download all samples"
    echo "--convert <list of ids>: specify which patients to convert"
    echo "--convert-num <top n>: specify how many patients to convert (top n by the total number of events)"
    echo "--default: use default settings (equal to --pip --icd9 --ccs --ndc --pnt --cms --do-convert)"
    echo "--default-omop: use default OMOP configuration (equal to --pip --apt --ccs --omop --psql)"
    echo "--icd9: downloads ICD9 definitions"
    echo "--ccs: downloads CCS ICD9 hierarchies"
    echo "--ndc: downloads NDC definitions"
    echo "--pnt: downloads the provider number table"
    echo "--cms: downloads the patient claims data"
    echo "--burst: splits the patient claim files for faster individual access"
    echo "--do-convert: converts patients"
    echo "--clean: removes all created files"
    echo "--clean-cache: removes cached files"
    echo "--update: updates the repository to the latest version (implies --clean-cache --pip --psql)"
    echo "--pip: install python packages"
    echo "--apt: use apt-get if available"
    echo "--psql: install python PostgreSQL connector (implies --pip)"
    echo "--omop: sets up the OMOP connection"
    echo "--shelve: use shelve input for conversion. (also switches to format_shelve.json except when -f is specified after)"
    echo "--nop: performs no operation besides basic setup tasks"
    exit 1
}

if [ $# -eq 0 ]; then
  usage
fi
while [ $# -gt 0 ]; do
  case "$1" in
  "")
    ;;
  -h)
    usage ;;
  -c)
    shift
    config="$1"
    ;;
  -f)
    shift
    format="$1"
    ;;
  -s)
    no_prompt=1
    ;;
  --samples)
    shift
    fetch_samples="$1"
    ;;
  --samples-all)
    fetch_samples="${CMS_SAMPLE_ALL}"
    ;;
  --convert)
    shift
    convert_list="$1"
    ;;
  --convert-num)
    shift
    convert_top_n="$1"
    ;;
  --default)
    pip=1
    icd9=1
    ccs=1
    ndc=1
    pn=1
    cms=1
    do_convert=1
    ;;
  --default-omop)
    pip=1
    ccs=1
    apt=1
    psql=1
    omop=1
    ;;
  --icd9)
    icd9=1
    ;;
  --ccs)
    ccs=1
    ;;
  --ndc)
    ndc=1
    ;;
  --pnt)
    pn=1
    ;;
  --opd)
    echo "--opd is now --cms"
    exit 8
    ;;
  --cms)
    cms=1
    ;;
  --burst)
    do_burst=1
    ;;
  --do-convert)
    do_convert=1
    ;;
  --clean)
    do_clean=1
    ;;
  --clean-cache)
    do_clean_cache=1
    ;;
  --update)
    do_clean_cache=1
    do_update=1
    pip=1
    psql=1
    ;;
  --omop)
    omop=1
    ;;
  --pip)
    pip=1
    ;;
  --apt)
    apt=1
    ;;
  --psql)
    pip=1
    psql=1
    ;;
  --shelve)
    format="format_shelve.json"
    shelve="--shelve"
    ;;
  --nop)
    do_nop=1
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

if [ ! -z $do_update ]; then
  git pull origin master
fi

# initialize git submodule if not done by user
git_submodule=`git submodule status | grep "^-"`
if [ ! -z "${git_submodule}" ]; then
  git submodule update --init --recursive
fi

if [ ! -z $do_clean_cache ]; then
  echo "clearing cached files"
  rm -- "${file_list}"
  rm -rf -- '${JSON_DIR}/*'
fi

cd_back() {
  cd "${base_dir}"
}

test_fail() {
  if [ $1 -ne 0 ]; then
    echo "setup failed!"
    cd_back
    exit 2
  fi
}

probe_open=`command -v open 2>/dev/null 1>&2; echo $?`
if [ "${probe_open}" -ne 0 ]; then
  pdf_open="evince"
else
  pdf_open="open"
fi

open_pdf() {
  `${pdf_open} $1`
}

curl_unzip() {
  curl -# -o "tmp.zip" "$1" && unzip -q "tmp.zip" && rm -- "tmp.zip"
  test_fail $?
}

prompt_echo() {
  if [ -z "${no_prompt}" ]; then
    echo "$@"
  fi
}

prompt() {
  abort=
  text=$1
  if [ $# -ge 2 ]; then
    read_url=$2
    text_url=" [i]nfo"
  else
    read_url=
    text_url=
  fi
  if [ $# -ge 3 ]; then
    read_terms=$3
    text_terms=" [t]erms"
  else
    read_terms=
    text_terms=
  fi
  if [ $# -ge 4 ]; then
    url_terms=$4
  else
    url_terms=
  fi
  if [ -z "${no_prompt}" ]; then
    while true; do
      read -p "${text} [y]es [n]o${text_url}${text_terms} [q]uit: " yn
      case $yn in
        [Yy]* )
          break
          ;;
        [Nn]* )
          abort=1
          break
          ;;
        [Tt]* )
          if [ ! -z "${read_terms}" ]; then
            if [ ! -f "${read_terms}" ]; then
              echo "downloading disclaimer and terms"
              curl -# -o "${read_terms}" "${url_terms}"
              test_fail $?
            fi
            open_pdf "${read_terms}"
          fi
          ;;
        [Ii]* )
          if [ ! -z "${read_url}" ]; then
            "${base_dir}/open_url.sh" -q -- "${read_url}"
          fi
          ;;
        [Qq]* )
          cd_back
          exit 3
          ;;
      esac
    done
  fi

  if [ ! -z "${abort}" ]; then
    return 1
  fi
  return 0
}

configure_value() {
  file=$1
  key=$2
  msg=$3
  default=$4
  read -p "${msg}: " value
  if [ ! -z "${value}" ]; then
    ./poke_json.py -f "${file}" -- "${key}" "${value}"
  else
    ./poke_json.py -f "${file}" -- "${key}" "${default}"
  fi
}

configure_bool() {
  file=$1
  key=$2
  msg=$3
  default=$4
  while true; do
    read -p "${msg}? [y]es [n]o: " resp
    if [ -z $resp ]; then
      ./poke_json.py -b -f "${file}" -- "${key}" "${default}"
      break
    fi
    case $resp in
      [Yy]* )
        ./poke_json.py -b -f "${file}" -- "${key}" "true"
        break
        ;;
      [Nn]* )
        ./poke_json.py -b -f "${file}" -- "${key}" "false"
        break
        ;;
    esac
  done
}

omop_configure() {
  if [ ! -f "${config}" ]; then
    cp -- "${config_omop}" "${config}"
  fi
  echo "configuring OMOP PostgreSQL database connection"
  ./poke_json.py -b -f "${config}" -- "omop_use_db" "true"
  configure_value "${config}" "omop_host" "database host (localhost)" "localhost"
  configure_value "${config}" "omop_port" "database port (5433)" "5433"
  configure_value "${config}" "omop_user" "database user (user)" "user"
  configure_value "${config}" "omop_passwd" "database password (password)" "password"
  configure_value "${config}" "omop_db" "database name (db)" "db"
  configure_value "${config}" "omop_schema" "database schema (schema)" "schema"
  configure_bool "${config}" "omop_use_alt_hierarchies" "use external CCS hierarchies (y)" "true"
  configure_bool "${config}" "use_cache" "use caching (y)" "true"
  echo "configuration can be found in '${config}'"
}

pip_install() {
  # install virtualenv first
  if [ ! -d ${venv} ]; then
    venv_version="12.1.1"
    venv_md5="901ecbf302f5de9fdb31d843290b7217"
    venv_dir="virtualenv-${venv_version}"
    venv_file="${venv_dir}.tar.gz"
    venv_url="https://pypi.python.org/packages/source/v/virtualenv/${venv_file}?md5=${venv_md5}"
    echo "downloading ${venv_url}"
    curl -# -o "${venv_file}" "${venv_url}"
    test_fail $?
    # FIXME temp ignore md5
    #md5 -q "${venv_file}" | xargs test "${venv_md5}" =
    #if [ $? != 0 ]; then
    #  echo "invalid md5 sum!"
    #  echo "expected ${venv_md5} got `md5 -q \"${venv_file}\"`"
    #  exit 10
    #fi
    tar xfz "${venv_file}"
    test_fail $?
    ${venv_dir}/virtualenv.py "${venv}"
    test_fail $?
    rm -rf -- "${venv_dir}"
    test_fail $?
    rm -- "${venv_file}"
    test_fail $?
  fi
  source ${venv_activate}
  test_fail $?
  if [ ! -z $apt ]; then
    no_apt_get=`command -v apt-get 2>/dev/null 1>&2; echo $?`
    if [ $no_apt_get == 0 ]; then
      echo "installing apt-get packages to speed up pip:"
      echo "sudo apt-get install git python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy libpq-dev python-dev" | "${SHELL}" -x
      test_fail $?
    fi
  fi
  echo "install python packages"
  pip install --upgrade pip
  pip install --upgrade -r requirements.txt
  if [ ! -z $psql ]; then
    pip install --upgrade psycopg2
  fi
  test_fail $?
}

venv_clean=
file_clean=()
allow_clean=
allow_stop=
ask_for_clean() {
  name=$1
  shift

  prompt "Do you want to remove ${name}?"
  if [ $? -eq 0 ]; then
    file_clean+=($@)
  fi
}

if [ ! -z "${omop}" ]; then
  omop_configure
fi

if [ ! -z "${pip}" ]; then
  if [ ! -z "${do_clean}" ]; then
    ask_for_clean "python virtualenv" "${venv}"
    for file in "${file_clean[@]}"; do
      echo "remove ${file}" && rm -r -- "${file}" 2> /dev/null
    done
    venv_clean=1
    file_clean=()
  fi
  pip_install
fi

if [ ! -z "${do_nop}" ]; then
  exit 0
fi

ask_all_clean() {
  allow_clean=1

  ask_for_clean "ICD9 definitions" "${ICD9_DIR}"
  ask_for_clean "CCS hierarchies" "${CCS_DIR}"
  ask_for_clean "NDC definitions" "${NDC_DIR}"
  ask_for_clean "provider numbers" "${PNT_DIR}"
  ask_for_clean "claims data" "${CMS_DIR}"
  ask_for_clean "patient files" "${JSON_DIR}" "${file_list}"
  ask_for_clean "error output files" "${err_file}" "${err_dict_file}"
  ask_for_clean "server logs" "${server_log}" "${server_err}"
  ask_for_clean "config files" "${config}"
  if [ -z ${venv_clean} ]; then
    ask_for_clean "python virtualenv" "${venv}"
  fi

  prompt "Do you want to stop the server?"
  if [ $? -eq 0 ]; then
    allow_stop=1
  fi
}

ask_clean() {
  prompt_echo "Cleaning removes files created by this script."
  if [ -z "${no_prompt}" ]; then
    while true; do
      read -p "What files do you want to remove? [a]ll [s]pecify [n]one [q]uit: " resp
      case $resp in
        [Aa]* )
          tmp="${no_prompt}"
          no_prompt=1
          ask_all_clean
          no_prompt="${tmp}"
          break
          ;;
        [Nn]* )
          break
          ;;
        [Ss]* )
          ask_all_clean
          break
          ;;
        [Qq]* )
          exit 5
          ;;
      esac
    done
  else
    ask_all_clean
  fi
}

clean() {
  for file in "${file_clean[@]}"; do
    echo "remove ${file}" && rm -r -- "${file}" 2> /dev/null
  done
  if [ ! -z $allow_stop ]; then
    echo "stop the server"
    ./start.sh -q --stop
  fi
}

allow_icd9=
ask_icd9() {
  ICD9_INFO="ftp://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD-9/ucreadme.txt"
  prompt "Do you want to download ICD9 definitions?" "${ICD9_INFO}"
  if [ $? -eq 0 ]; then
    allow_icd9=1
  fi
}

fetch_icd9() {
  ICD9_URL="ftp://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD-9/ucod.txt"
  if [ ! -d "${ICD9_DIR}" ]; then
    mkdir -p "${ICD9_DIR}"
  fi
  if [ ! -f "${ICD9_DIR}/ucod.txt" ]; then
    cd "${ICD9_DIR}"
    echo "downloading ICD9 definitions"
    curl -# -o "ucod.txt" "${ICD9_URL}"
    # temporary quick fix for encoding issues
    grep 386.0 ucod.txt | hexdump | grep 82 > /dev/null
    if [ $? -eq 0 ]; then
      echo "fixing encoding issues"
      iconv -f ibm437 -t utf-8 ucod.txt > ucod2.txt
      test_fail $?
      mv ucod.txt ucod_old.txt
      test_fail $?
      mv ucod2.txt ucod.txt
      test_fail $?
    fi
    cd_back
  fi
}

allow_ccs=
ask_ccs() {
  CCS_INFO="http://www.hcup-us.ahrq.gov/toolssoftware/ccs/ccs.jsp"
  prompt "Do you want to download the CCS ICD9 hierarchies?" "${CCS_INFO}"
  if [ $? -eq 0 ]; then
    allow_ccs=1
  fi
}

fetch_ccs() {
  CCS_SINGLE_DIAG_URL="http://www.hcup-us.ahrq.gov/toolssoftware/ccs/AppendixASingleDX.txt"
  CCS_SINGLE_PROC_URL="http://www.hcup-us.ahrq.gov/toolssoftware/ccs/AppendixBSinglePR.txt"
  CCS_MULTI_DIAG_URL="http://www.hcup-us.ahrq.gov/toolssoftware/ccs/AppendixCMultiDX.txt"
  CCS_MULTI_PROC_URL="http://www.hcup-us.ahrq.gov/toolssoftware/ccs/AppendixDMultiPR.txt"
  if [ ! -d "${CCS_DIR}" ]; then
    mkdir -p "${CCS_DIR}"
  fi
  if [ ! -f "${CCS_DIR}/single_diag.txt" ] || [ ! -f "${CCS_DIR}/single_proc.txt" ] || [ ! -f "${CCS_DIR}/multi_diag.txt" ] || [ ! -f "${CCS_DIR}/multi_proc.txt" ]; then
    cd "${CCS_DIR}"
    echo "downloading CCS hierarchies"
    curl -# -o "single_diag.txt" "${CCS_SINGLE_DIAG_URL}"
    curl -# -o "single_proc.txt" "${CCS_SINGLE_PROC_URL}"
    curl -# -o "multi_diag.txt" "${CCS_MULTI_DIAG_URL}"
    curl -# -o "multi_proc.txt" "${CCS_MULTI_PROC_URL}"
    cd_back
  fi
}

allow_ndc=
ask_ndc() {
  NDC_INFO="http://www.fda.gov/Drugs/InformationOnDrugs/ucm142438.htm"
  prompt "Do you want to download NDC definitions?" "${NDC_INFO}"
  if [ $? -eq 0 ]; then
    allow_ndc=1
  fi
}

fetch_ndc() {
  NDC_URL="http://www.fda.gov/downloads/Drugs/DevelopmentApprovalProcess/UCM070838.zip"
  if [ ! -d "${NDC_DIR}" ]; then
    mkdir -p "${NDC_DIR}"
  fi
  if [ ! -f "${NDC_DIR}/product.txt" ] || [ ! -f "${NDC_DIR}/package.txt" ]; then
    cd "${NDC_DIR}"
    echo "downloading NDC definitions"

    curl_unzip "${NDC_URL}"
    rm -- "product.xls" "package.xls"
    cd_back
  fi
}

allow_pn=
ask_pn() {
  PN_INFO="http://www.resdac.org/cms-data/variables/provider-number"
  prompt "Do you want to download provider numbers?" "${PN_INFO}"
  if [ $? -eq 0 ]; then
    allow_pn=1
  fi
}

fetch_pn() {
  PNT_URL="http://www.resdac.org/sites/resdac.org/files/Provider%20Number%20Table.txt"
  if [ ! -d "${PNT_DIR}" ]; then
    mkdir -p "${PNT_DIR}"
  fi
  if [ ! -f "${PNT_DIR}/pnt.txt" ]; then
    cd "${PNT_DIR}"
    echo "downloading provider numbers"
    curl -# -o "pnt.txt" "${PNT_URL}"
    cd_back
  fi
}

allow_cms=
ask_cms() {
  CMS_INFO="http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF.html"
  CMS_DISCLAIMER="http://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/BSAPUFS/Downloads/PUF_Disclaimer.pdf"
  CMS_DISCLAIMER_FILE="disclaimer.pdf"
  if [ ! -d "${CMS_DIR}" ]; then
    mkdir -p "${CMS_DIR}"
  fi
  cd "${CMS_DIR}"
  samples="$1"
  sample_count=`echo "${samples}" | wc -w | tr -d "[[:space:]]"`
  approx_gb=`echo "${samples}" | wc -w | sed -e "s/$/*3/" | bc` # pessimistic estimate of 3GB per sample
  prompt_echo "Preparing to download ${sample_count} sample[s] of the patient claims data."
  prompt_echo "The download may take a while (~${approx_gb}GB)."
  prompt "Do you want to download claims data?" "${CMS_INFO}" "${CMS_DISCLAIMER_FILE}" "${CMS_DISCLAIMER}"
  if [ $? -eq 0 ]; then
    allow_cms=1
  fi

  cd_back
}

fetch_cms() {
  if [ ! -d "${CMS_DIR}" ]; then
    mkdir -p "${CMS_DIR}"
  fi
  cd "${CMS_DIR}"
  samples="$1"
  for i in $samples; do
    valid_sample=`echo $i | grep -E "[1-9]|1[0-9]|20"`
    if [ -z "${valid_sample}" ]; then
      echo "invalid sample '${i}'"
    else
      echo "downloading sample ${i}"
      curl_unzip "http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/DE1_0_2008_Beneficiary_Summary_File_Sample_${i}.zip"
      curl_unzip "http://downloads.cms.gov/files/DE1_0_2008_to_2010_Carrier_Claims_Sample_${i}A.zip"
      curl_unzip "http://downloads.cms.gov/files/DE1_0_2008_to_2010_Carrier_Claims_Sample_${i}B.zip"
      curl_unzip "http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/DE1_0_2008_to_2010_Inpatient_Claims_Sample_${i}.zip"
      curl_unzip "http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/DE1_0_2008_to_2010_Outpatient_Claims_Sample_${i}.zip"
      curl_unzip "http://downloads.cms.gov/files/DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_${i}.zip"
      curl_unzip "http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/DE1_0_2009_Beneficiary_Summary_File_Sample_${i}.zip"
      curl_unzip "http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/DE1_0_2010_Beneficiary_Summary_File_Sample_${i}.zip"
    fi
  done
  echo "done downloading samples"

  cd_back
}

burst() {
  echo "bursting samples for faster random access"
  ./burst.py --path "${CMS_DIR}" -c "${config}" -f "${format}"
  test_fail $?
}

allow_convert=
ask_convert() {
  prompt_echo "Converting patient files can take a while."
  prompt "Do you want to convert some patient files?"
  if [ $? -eq 0 ]; then
    allow_convert=1
  fi
}

convert_patients() {
  if [ ! -d "${JSON_DIR}" ]; then
    mkdir -p "${JSON_DIR}"
  fi

  if [ -z "${convert_list}" ]; then
    echo "find top ${convert_top_n} patients"
    if [ -z $shelve ]; then
      ids=`./cms_analyze.py -m -f "${format}" -- ${CMS_DIR} | tail -n ${convert_top_n}`
    else
      # FIXME not the top n patients!
      ids=`./shelve_access.py -c "${config}" -l | cut -d" " -f1 | head -n ${convert_top_n}`
    fi
  else
    ids="${convert_list}"
  fi
  for id in $ids; do
    file="${JSON_DIR}/${id}.json"
    echo "create ${file}"
    echo "config file is '${config}' format file is '${format}'"
    echo "script output can be found in ${err_file} and ${err_dict_file}"
    if [ -z $shelve ]; then
      ./cms_get_patient.py -p "${id}" -f "${format}" -o "${file}" -c "${style_classes}" -- "${CMS_DIR}" 2>> $err_file
      if [ $? -ne 0 ]; then
        echo "failed during patient conversion"
        cd_back
        exit 6
      fi
    else
      ./shelve_access.py -p "${id}" -c "${config}" | ./cms_get_patient.py -p "${id}" -f "${format}" -o "${file}" -c "${style_classes}" -- - 2>> $err_file
      if [ $? -ne 0 ]; then
        echo "failed during patient conversion"
        cd_back
        exit 9
      fi
    fi
    ./build_dictionary.py -p "${file}" -c "${config}" -o "${dictionary}" 2>> $err_dict_file
    if [ $? -ne 0 ]; then
      echo "failed during dictionary creation"
      cd_back
      exit 7
    fi
    echo "conversion successful"
  done

  ./start.sh --list-update
}

# ask user for permission
if [ ! -z $do_clean ]; then
  ask_clean
fi
if [ ! -z $cms ]; then
  ask_cms "${fetch_samples}"
fi
if [ ! -z $icd9 ]; then
  ask_icd9
fi
if [ ! -z $ccs ]; then
  ask_ccs
fi
if [ ! -z $ndc ]; then
  ask_ndc
fi
if [ ! -z $pn ]; then
  ask_pn
fi
if [ ! -z $do_convert ]; then
  ask_convert
fi

prompt_echo "=== no user input required after this point ==="

# execute ops
if [ ! -z $allow_clean ]; then
  clean
fi
if [ ! -z $allow_cms ]; then
  fetch_cms "${fetch_samples}"
fi
if [ ! -z $allow_icd9 ]; then
  fetch_icd9
fi
if [ ! -z $allow_ccs ]; then
  fetch_ccs
fi
if [ ! -z $allow_ndc ]; then
  fetch_ndc
fi
if [ ! -z $allow_pn ]; then
  fetch_pn
fi
if [ ! -z $do_burst ]; then
  burst
fi
if [ ! -z $allow_convert ]; then
  convert_patients
fi
