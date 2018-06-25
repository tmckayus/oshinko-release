#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
. oshinko_webui.sh
. oshinko_s2i.sh
. openshift_spark.sh
. oc_proxy.sh

# Currently the script makes the following assumptions:
#   1) Argument syntax is wellformed (Currently not validated)
#   2) All argument data is valid (i.e. user/repo/token exist)
#   3) Concreate is already installed on the host
#   4) Git is already installed
#   5) Script has permissions to write to the directory passed in
#   6) Tempdir is empty (will be wiped if it's not)

function main(){
  QUIET="false"
  STAGE=-1
  while getopts "hqs:" opt; do
    case ${opt} in
      h)
        usage
        exit 0
        ;;
      q)
        QUIET="true"
        ;;
      s)
        STAGE=$OPTARG
        ;;
      \?)
        echo "Invalid option" >&2
        usage
        exit 1
        ;;
      :)
        echo "Option -$OPTARG requires an argument." >&2
        exit 1
        ;;
    esac
  done

  shift "$((OPTIND-1))"

  if [ "$#" -ne 8 ]; then
    echo "Error: 8 Positional arguments are required." >&2
    usage
    exit 1
  fi

  USER=$1
  REPO=$2
  GITHUB_TOKEN=$3
  TMPDIR=$4
  VERSION=$5
  PROJECT=$6
  COMMIT_AUTHOR=$7
  COMMIT_EMAIL=$8

  setup_wdir
  mkdir $TMPDIR/project_report
  REPORT_DIR=$TMPDIR/project_report

  git config user.name ${COMMIT_AUTHOR}
  git config user.email ${COMMIT_EMAIL}

  case ${PROJECT} in
    openshift-spark)
      openshift_spark 2>&1 | tee -a ${REPORT_DIR}/outfile.txt
      ;;
    oshinko-webui)
      oshinko_webui 2>&1 | tee -a ${REPORT_DIR}/outfile.txt
      ;;
    oshinko-s2i)
      oshinko_s2i 2>&1 | tee -a ${REPORT_DIR}/outfile.txt
      ;;
    oc-proxy)
      oc_proxy 2>&1 | tee -a ${REPORT_DIR}/outfile.txt
      ;;
    *)
      echo "Error: Project not recognized." 2>&1 | tee -a ${REPORT_DIR}/outfile.txt
      usage
      exit 1
      ;;
  esac

  exit ${PIPESTATUS[0]}
}

function setup_wdir(){
  rm ${TMPDIR}/* -rf
  cd ${TMPDIR}
  git clone https://${USER}:${GITHUB_TOKEN}@github.com/${USER}/${REPO}.git
  cd ${REPO}
}

function usage() {
  echo
  echo "Tag the latest commit with vA.B.C."
  echo
  echo "Usage: ./repo_ctrl OWNER REPO TOKEN TMPDIR VERSION PROJECT AUTHOR EMAIL"
  echo
  echo "required arguments"
  echo
  echo "  OWNER               The owner of the PROJECT repository"
  echo "  REPO                The PROJECT repository name."
  echo "  TOKEN               The commiter's auth token."
  echo "  TMPDIR              The temporary working directory."
  echo "  VERSION             The version to update to."
  echo "  PROJECT             The project to operate on. Project can be one of:"
  echo "                      [openshift-spark|oshinko-cli|oshinko-webui|oshinko-s2i|oc-proxy]"
  echo
  echo "  AUTHOR              The committer & author:"
  echo "  EMAIL               The committer's email:"
  echo
  echo "optional arguments:"
  echo "  -q                  Run script in quiet mode, i.e. no permanent changes made to upstream."
  echo "                      This is useful for generating a mock report of to-be-made changes."
  echo "  -h                  Show this message"
  echo "  -s                  If a project operates in stages, specify a stage here, [0-9]."
}

main $@
exit $?