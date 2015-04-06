#!/bin/bash
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-16 09:00

NDC_DIR="code/ndc"
ICD9_DIR="code/icd9"
CCS_DIR="code/ccs"
OPD_DIR="opd"
JSON_DIR="json"
OPD_SAMPLE_ALL=`seq -s " " 1 20`

base_dir=`pwd`
convert_top_n=3
convert_list=
dictionary="${JSON_DIR}/dictionary.json"
config="config.txt"
format="format.json"
err_file="err.txt"
err_dict_file="err_dict.txt"
server_log="server_log.txt"
server_err="server_err.txt"
file_list="patients.txt"
fetch_samples="10"

no_prompt=
ndc=
opd=
icd9=
ccs=
pip=
do_convert=
do_clean=
do_nop=
do_burst=

USAGE="Usage: $0 -hs [-c <dictionary config file>] [-f <table format file>] [--samples <list of samples>] [--samples-all] [--convert <list of ids>] [--convert-num <top n>] [--default] [--icd9] [--ccs] [--ndc] [--opd] [--burst] [--do-convert] [--clean] [--pip] [--nop]"

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
    echo "--default: use default settings (equal to --icd9 --ccs --ndc --opd --do-convert)"
    echo "--icd9: downloads ICD9 definitions"
    echo "--ccs: downloads CCS ICD9 hierarchies"
    echo "--ndc: downloads NDC definitions"
    echo "--opd: downloads the patient claims data"
    echo "--burst: splits the patient claim files for faster individual access"
    echo "--do-convert: converts patients"
    echo "--clean: removes all created files"
    echo "--pip: install python packages. (not required for all use cases)"
    echo "--nop: performs no operation besides basic setup tasks"
    exit 1
}

if [ $# -eq 0 ]; then
  usage
fi
while [ $# -gt 0 ]; do
  case "$1" in
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
    fetch_samples="${OPD_SAMPLE_ALL}"
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
    icd9=1
    ccs=1
    ndc=1
    opd=1
    do_convert=1
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
  --opd)
    opd=1
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
  --pip)
    pip=1
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

# initialize git submodule if not done by user
git_submodule=`git submodule status | grep "^-"`
if [ ! -z "${git_submodule}" ]; then
  git submodule init
  git submodule update
fi

if [ ! -z "${pip}" ]; then
  probe_pip=`command -v pip 2>/dev/null 1>&2; echo $?`
  if [ "${probe_pip}" -ne 0 ]; then
    echo "pip is required to install python dependencies"
    echo "TODO pip install is not implemented yet!"
    exit 0
  fi
  echo "TODO python packages install is not implemented yet!"
fi

if [ ! -z "${do_nop}" ]; then
  exit 0
fi

cd_back() {
  cd "${base_dir}"
}

test_fail() {
  if [ $1 -ne 0 ]; then
    echo "setup failed!"
    cd_back
    exit 1
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
          exit 0
          ;;
      esac
    done
  fi

  if [ ! -z "${abort}" ]; then
    return 1
  fi
  return 0
}

allow_clean=
allow_stop=
file_clean=()
ask_for_clean() {
  name=$1
  shift

  prompt "Do you want to remove ${name}?"
  if [ $? -eq 0 ]; then
    file_clean+=($@)
  fi
}

ask_all_clean() {
  allow_clean=1

  ask_for_clean "ICD9 definitions" "${ICD9_DIR}"
  ask_for_clean "CCS hierarchies" "${CCS_DIR}"
  ask_for_clean "NDC definitions" "${NDC_DIR}"
  ask_for_clean "claims data" "${OPD_DIR}"
  ask_for_clean "patient files" "${JSON_DIR}" "${file_list}"
  ask_for_clean "error output files" "${err_file}" "${err_dict_file}"
  ask_for_clean "server logs" "${server_log}" "${server_err}"
  ask_for_clean "config files" "${config}"

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
          exit 0
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
    grep 386.0 ucod.txt | hexdump | grep 82
    if [ -z $? ]; then
      echo "fixing encoding issues"
      iconv -f ibm437 -t utf-8 > ucod2.txt
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

allow_opd=
ask_opd() {
  OPD_INFO="http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF.html"
  OPD_DISCLAIMER="http://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/BSAPUFS/Downloads/PUF_Disclaimer.pdf"
  OPD_DISCLAIMER_FILE="disclaimer.pdf"
  if [ ! -d "${OPD_DIR}" ]; then
    mkdir -p "${OPD_DIR}"
  fi
  cd "${OPD_DIR}"
  samples="$1"
  sample_count=`echo "${samples}" | wc -w | tr -d "[[:space:]]"`
  approx_gb=`echo "${samples}" | wc -w | sed -e "s/$/*3/" | bc` # pessimistic estimate of 3GB per sample
  prompt_echo "Preparing to download ${sample_count} sample[s] of the patient claims data."
  prompt_echo "The download may take a while (~${approx_gb}GB)."
  prompt "Do you want to download claims data?" "${OPD_INFO}" "${OPD_DISCLAIMER_FILE}" "${OPD_DISCLAIMER}"
  if [ $? -eq 0 ]; then
    allow_opd=1
  fi

  cd_back
}

fetch_opd() {
  if [ ! -d "${OPD_DIR}" ]; then
    mkdir -p "${OPD_DIR}"
  fi
  cd "${OPD_DIR}"
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
  echo "TODO burst not implemented yet!"
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
    ids=`./opd_analyze.py -m -f "${format}" -- ${OPD_DIR} | tail -n ${convert_top_n}`
  else
    ids="${convert_list}"
  fi
  for id in $ids; do
    file="${JSON_DIR}/${id}.json"
    echo "create ${file}"
    echo "config file is ${config}"
    echo "script output can be found in ${err_file} and ${err_dict_file}"
    ./opd_get_patient.py -p "${id}" -f "${format}" -o "${file}" -- "${OPD_DIR}" 2> $err_file || {
      echo "failed during patient conversion"
      cd_back
      exit 1
    }
    ./build_dictionary.py -p "${file}" -c "${config}" -o "${dictionary}" 2> $err_dict_file || {
      echo "failed during dictionary creation"
      cd_back
      exit 1
    }
    echo "conversion successful"
  done

  ./start.sh --list-update
}

# ask user for permission
if [ ! -z $do_clean ]; then
  ask_clean
fi
if [ ! -z $opd ]; then
  ask_opd "${fetch_samples}"
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
if [ ! -z $do_convert ]; then
  ask_convert
fi

prompt_echo "=== no user input required after this point ==="

# execute ops
if [ ! -z $allow_clean ]; then
  clean
fi
if [ ! -z $allow_opd ]; then
  fetch_opd "${fetch_samples}"
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
if [ ! -z $do_burst ]; then
  burst
fi
if [ ! -z $allow_convert ]; then
  convert_patients
fi
