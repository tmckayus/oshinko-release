#!/bin/bash

TEST_DIR=$(readlink -f `dirname "${BASH_SOURCE[0]}"` | grep -o '.*/oshinko-release/test/e2e')
source $TEST_DIR/common

set_template oshinko-scala-spark-build-dc
set_git_uri https://github.com/radanalyticsio/s2i-integration-test-apps
set_app_main_class org.apache.spark.examples.SparkPi
get_templates

os::test::junit::declare_suite_start "$MY_SCRIPT"

echo "++ test_versions"
test_versions $S2I_TEST_IMAGE_SCALA

os::test::junit::declare_suite_end
