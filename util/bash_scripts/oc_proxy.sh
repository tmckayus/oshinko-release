#!/usr/bin/env bash

oc_proxy () {
  # Tag the latest commit with vA.B.C
  tag_latest
}


function tag_latest(){
  TAG=v${VERSION}

  echo "-----------------------------------------------------"
  echo "Tagging latest branch to ${TAG}"
  echo "-----------------------------------------------------"

  git tag ${TAG}

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
