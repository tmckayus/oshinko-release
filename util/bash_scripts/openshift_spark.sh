#!/usr/bin/env bash

# Writes tag & branch version to a json file

openshift_spark () {
  BRANCH=`echo ${VERSION} | grep -o '^[0-9]\.[0-9]'`
  GH_INFO=${REPORT_DIR}/gh_info.txt
  echo "<<tag>> ${BRANCH}" > ${GH_INFO}
  branch_update
  tag_update
}

function master_update(){
  echo "Run change-yaml.sh"
  ./change-yaml.sh ${VERSION}

  echo "regenerate the *-build directory"
  make clean-context
  make context
  make zero-tarballs
  git add openshift-spark-build

  echo "Report the changes"
  git status
  git --no-pager diff --cached

  echo "Commit the changes to master branch"
  git commit --author="${COMMIT_AUTHOR} <${COMMIT_EMAIL}>" -m "Spark version update for openshift-spark"

  if [ "${QUIET}" = "true" ] ; then
    echo
    echo "COMMAND OMITTED:"
    echo "git push https://<GITHUB_TOKEN>@github.com/${USER}/${REPO} master"
    echo
  else
    echo "### PUSHING TO REPO ${USER}/${REPO} master ###"
    git push https://${GITHUB_TOKEN}@github.com/${USER}/${REPO} master
  fi
}

function branch_update(){
  echo "---------------------------------------------------------"
  echo "Create a new branch ${BRANCH} for the new spark version."
  echo "---------------------------------------------------------"

  git checkout -b ${BRANCH}
  if [ "${QUIET}" = "true" ] ; then
    echo
    echo "COMMAND OMITTED:"
    echo "git push https://<GITHUB_TOKEN>@github.com/${USER}/${REPO} ${BRANCH}"
    echo
  else
    echo "### PUSHING TO REPO ${USER}/${REPO} ${BRANCH} ###"
    git push https://${GITHUB_TOKEN}@github.com/${USER}/${REPO} ${BRANCH}
  fi
}

function tag_update(){
  echo "-----------------------------------------------------"
  echo "Tag the commit on a branch with X.Y.0-1"
  echo "-----------------------------------------------------"
  git checkout ${BRANCH}
  tag_sh_output="$(./tag.sh 2>&1)"

  echo -e "${tag_sh_output}"
  TAG=`echo -e "${tag_sh_output}" | grep 'Adding tag *' | sed "s/Adding tag //g"`

  ACTUAL_TAG=`git describe --tags`
  # Verify:
  if [ "${TAG}" = "${ACTUAL_TAG}" ] ; then
    echo "Tag was successfully updated. Good to push."
  else
    printf  "Tag was not successfully updated.\nTag retrieved from tag.sh: ${TAG}\nTag retrieved from [git tag --list]: ${ACTUAL_TAG}\n"
    exit 1
  fi

  sed -i "s/<<tag>>/${TAG}/g" ${GH_INFO}

  if [ "${QUIET}" = "true" ] ; then
    echo
    echo "COMMAND OMITTED:"
    echo "git push https://<GITHUB_TOKEN>@github.com/${USER}/${REPO} ${TAG}"
    echo
  else
    echo "### PUSHING TO REPO ${USER}/${REPO} ${TAG} ###"
    git push https://${GITHUB_TOKEN}@github.com/${USER}/${REPO} ${TAG}
  fi
}