#!/usr/bin/env bash

oshinko_s2i () {
   case ${STAGE} in
    0)
      release_branch
      ;;
    1)
      tag_latest
      ;;
    *)
      echo "Error: Stage not recognized, oshinko-s2i accepts 2 stages [0: release branch | 1: tag latest]" >&2
      usage
      exit 1
      ;;
  esac
}

function release_branch(){
  BRANCH=release${VERSION}

  echo "-----------------------------------------------------"
  echo "Creating a new release branch ${BRANCH}"
  echo "-----------------------------------------------------"

  git checkout -b ${BRANCH}

  echo "Run change-yaml.sh"
  ./change-yaml.sh ${VERSION}

  echo "Regenerate the *-build directory"
  ./make-build-dirs.sh

  echo "Report the changes"
  git status
  git --no-pager diff --cached

  echo "Commit the changes to release${VERSION} branch"
  git commit --author="${COMMIT_AUTHOR} <${COMMIT_EMAIL}>" -m "Release update for Oshinko"

  if [ "${QUIET}" = "true" ] ; then
    echo
    echo "COMMAND OMITTED:"
    echo "git push https://<GITHUB_TOKEN>@github.com/${USER}/${REPO} ${BRANCH}"
    echo
  else
    echo "### PUSHING TO REPO ${USER}/${REPO} master ###"
    git push https://${GITHUB_TOKEN}@github.com/${USER}/${REPO} ${BRANCH}
  fi
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