#!/bin/bash
set -e
function push_tag() {
    docker push docker.io/radanalyticsio/radanalytics-pyspark:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-pyspark-py36:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-java-spark:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-scala-spark:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-pyspark-inc:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-pyspark-py36-inc:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-java-spark-inc:$1 || return 1
    docker push docker.io/radanalyticsio/radanalytics-scala-spark-inc:$1 || return 1
    docker push docker.io/radanalyticsio/oshinko-rest:$1 || return 1
    docker push docker.io/radanalyticsio/oshinko-webui:$1 || return 1
    docker push docker.io/radanalyticsio/oc-proxy:$1 || return 1
}

if [ "$#" -ne 1 ]; then
    echo "Usage: push_tag.sh TAG"
    echo Push local radanalyticsio s2i and oshinko images tagged with TAG to docker.io
    exit 1
fi

push_tag $1
if [ "$?" -eq 0 ]; then
    echo
    echo "Tagged images pushed successfully"
else
    echo
    echo "Failed to push tagged images"
    exit -1
fi
