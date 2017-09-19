#/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: versioned-resources-yaml.sh VERSION-TAG"
    exit 1
fi

mkdir release_templates
rm -rf release_templates/*

cd release_templates; wget https://radanalytics.io/resources.yaml

sed -r -i "s@(radanalyticsio/radanalytics.*spark)(:stable)@\1:$1@" *
sed -r -i "s@(radanalyticsio/oshinko-webui)(:stable)@\1:$1@" *

echo "Successfully wrote templates to release_templates/ with version tag $1"
echo
echo "grep radanalyticsio/radanalytics.*spark:$1 *"
echo
grep radanalyticsio/radanalytics.*spark:$1 *
echo
echo "grep radanalyticsio/oshinko-webui:$1 *"
echo
grep radanalyticsio/oshinko-webui:$1 *

