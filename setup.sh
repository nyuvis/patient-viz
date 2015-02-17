#!/bin/sh
# @author Joschi <josua.krause@gmail.com>
# created 2015-02-16 09:00

NDC_DIR="code/ndc"
OPD_DIR="opd"
JSON_DIR="json"
OPD_SAMPLE_ALL=`seq -s " " -t "" 1 20`

base_dir=`pwd`
convert_top_n=3
convert_list=
dictionary="${JSON_DIR}/dictionary.json"
config="config.txt"
err_file="err.txt"
err_dict_file="err_dict.txt"
fetch_samples="10"
no_prompt=
ndc=
opd=
do_convert=
do_clean=

USAGE="Usage: $0 -hs [--samples <list of samples>] [--samples-all] [--convert <list of ids>] [--convert-num <top n>] [--default] [--ndc] [--opd] [--do-convert] [--clean]"

usage() {
    echo $USAGE
    echo "-h: print help"
    echo "-s: do not prompt the user for input"
    echo "--samples <list of samples>: specify which samples to download (1-20)"
    echo "--samples-all: download all samples"
    echo "--convert <list of ids>: specify which patients to convert"
    echo "--convert-num <top n>: specify how many patients to convert (top n by the total number of events)"
    echo "--default: use default settings (equal to --ndc --opd --do-convert)"
    echo "--ndc: downloads the NDC database"
    echo "--opd: downloads the patient claims data"
    echo "--do-convert: converts patients"
    echo "--clean: removes all created files"
    exit 1
}

if [ $# -eq 0 ]; then
  usage
fi
while [ $# -gt 0 ]; do
  case "$1" in
  -h)
    usage ;;
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
    ndc=1
    opd=1
    do_convert=1
    ;;
  --ndc)
    ndc=1
    ;;
  --opd)
    opd=1
    ;;
  --do-convert)
    do_convert=1
    ;;
  --clean)
    do_clean=1
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
git_submodule=`git submodule status`
if [ -z "${git_submodule}" ]; then
  git submodule init
  git submodule update
fi

cd_back() {
  cd "${base_dir}"
}

test_fail() {
  if [ $1 -ne 0 ]; then
    echo "fail!"
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

clean() {
  echo "removing ${NDC_DIR}" && rm -r "${NDC_DIR}"
  echo "removing ${OPD_DIR}" && rm -r "${OPD_DIR}"
  echo "removing ${JSON_DIR}" && rm -r "${JSON_DIR}"
  echo "removing ${err_file} and ${err_dict_file}" && rm "${err_file}" "${err_dict_file}"
}

fetch_ndc() {
  NDC_ZIP="ndc.zip"
  NDC_URL="http://www.fda.gov/downloads/Drugs/DevelopmentApprovalProcess/UCM070838.zip"
  NDC_INFO="http://www.fda.gov/Drugs/InformationOnDrugs/ucm142438.htm"
  if [ ! -d "${NDC_DIR}" ]; then
    mkdir -p "${NDC_DIR}"
  fi
  if [ ! -f "${NDC_DIR}/product.txt" ] || [ ! -f "${NDC_DIR}/package.txt" ]; then
    cd "${NDC_DIR}"
    echo "downloading NDC database"
    echo "more infos at ${NDC_INFO}"
    curl -# -o "${NDC_ZIP}" "${NDC_URL}" && unzip "${NDC_ZIP}" && rm "${NDC_ZIP}" "product.xls" "package.xls"
    test_fail $?
    cd_back
  fi
}

curl_unzip() {
  curl -# -o "tmp.zip" "$1" && unzip "tmp.zip" && rm "tmp.zip"
  test_fail $?
}

fetch_opd() {
  OPD_INFO="http://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF.html"
  OPD_DISCLAIMER="http://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/BSAPUFS/Downloads/PUF_Disclaimer.pdf"
  OPD_DISCLAIMER_FILE="disclaimer.pdf"
  if [ ! -d "${OPD_DIR}" ]; then
    mkdir -p "${OPD_DIR}"
  fi
  cd "${OPD_DIR}"
  samples="$1"
  # show disclaimer and info page
  echo "preparing to download samples ${samples} of the patient claims data"
  echo "more infos at ${OPD_INFO}"
  if [ ! -f "${OPD_DISCLAIMER_FILE}" ]; then
    echi "downloading disclaimer and terms"
    curl -# -o "${OPD_DISCLAIMER_FILE}" "${OPD_DISCLAIMER}"
    test_fail $?
  fi
  # user confirmation
  abort=
  approx_gb=`echo "${samples}" | wc -w | sed -e "s/$/*3/" | bc` # pessimistic estimate of 3GB per sample
  echo "by downloading you agree to the terms for the claims data"
  echo "the download can take a while (~${approx_gb}GB)"
  if [ -z "${no_prompt}" ]; then
    while true; do
      read -p "Do you wish to continue? y - yes; n - no; r - read terms: " yn
      case $yn in
        [Yy]* )
          break
          ;;
        [Nn]* )
          abort=1
          break
          ;;
        [Rr]* )
          open_pdf "${OPD_DISCLAIMER_FILE}"
          ;;
      esac
    done
  fi

  if [ ! -z "${abort}" ]; then
    cd_back
    return
  fi

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

convert_patients() {
  if [ ! -d "${JSON_DIR}" ]; then
    mkdir -p "${JSON_DIR}"
  fi

  if [ -z "${convert_list}" ]; then
    echo "find top ${convert_top_n} patients"
    ids=`./opd_analyze.py -m ${OPD_DIR} | tail -n ${convert_top_n}`
  else
    ids="${convert_list}"
  fi
  for id in $ids; do
    file="${JSON_DIR}/${id}.json"
    echo "create ${file}"
    echo "config file is ${config}"
    echo "script output can be found in ${err_file} and ${err_dict_file}"
    ./opd_get_patient.py -p "${id}" -o "${file}" -- "${OPD_DIR}" 2> $err_file || {
      echo "failed during patient conversion"
      cd_back
      exit 1
    }
    ./build_dictionary.py -p "${file}" -c "$config" -o "${dictionary}" 2> $err_dict_file || {
      echo "failed during dictionary creation"
      cd_back
      exit 1
    }
  done

  ls -A "${JSON_DIR}/*.json" | grep -v "${dictionary}" > patients.txt
}

if [ ! -z $do_clean ]; then
  clean
fi
if [ ! -z $opd ]; then
  fetch_opd "${fetch_samples}"
fi
if [ ! -z $ndc ]; then
  fetch_ndc
fi
if [ ! -z $do_convert ]; then
  convert_patients
fi
