#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Usage: set_tag.sh VERSION TAG"
    echo Pull radanalyticsio s2i and oshinko images from docker.io with the tag VERSION, and apply a new tag TAG
    exit -1
fi

#set -e
function pull_and_tag() {
    docker pull docker.io/radanalyticsio/radanalytics-pyspark:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-pyspark-py36:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-java-spark:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-scala-spark:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-pyspark-inc:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-pyspark-py36-inc:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-java-spark-inc:$1 || return 1
    docker pull docker.io/radanalyticsio/radanalytics-scala-spark-inc:$1 || return 1
    docker pull docker.io/radanalyticsio/oshinko-rest:$1 || return 1
    docker pull docker.io/radanalyticsio/oshinko-webui:$1 || return 1
    docker pull docker.io/radanalyticsio/oc-proxy:$1 || return 1

    docker tag docker.io/radanalyticsio/radanalytics-pyspark:$1 docker.io/radanalyticsio/radanalytics-pyspark:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-pyspark-py36:$1 docker.io/radanalyticsio/radanalytics-pyspark-py36:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-java-spark:$1 docker.io/radanalyticsio/radanalytics-java-spark:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-scala-spark:$1 docker.io/radanalyticsio/radanalytics-scala-spark:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-pyspark-inc:$1 docker.io/radanalyticsio/radanalytics-pyspark-inc:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-pyspark-py36-inc:$1 docker.io/radanalyticsio/radanalytics-pyspark-py36-inc:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-java-spark-inc:$1 docker.io/radanalyticsio/radanalytics-java-spark-inc:$2 || return 1
    docker tag docker.io/radanalyticsio/radanalytics-scala-spark-inc:$1 docker.io/radanalyticsio/radanalytics-scala-spark-inc:$2 || return 1
    docker tag docker.io/radanalyticsio/oshinko-rest:$1 docker.io/radanalyticsio/oshinko-rest:$2 || return 1
    docker tag docker.io/radanalyticsio/oshinko-webui:$1 docker.io/radanalyticsio/oshinko-webui:$2 || return 1
    docker tag docker.io/radanalyticsio/oc-proxy:$1 docker.io/radanalyticsio/oc-proxy:$2 || return 1
}

pull_and_tag $1 $2
if [ "$?" -eq 0 ]; then
    echo
    echo "Images pulled and tagged successfully"
else
    echo
    echo "Failed to pull and tag all images"
    exit -1
fi
