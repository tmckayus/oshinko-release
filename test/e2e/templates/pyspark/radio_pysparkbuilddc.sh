#!/bin/bash

TEST_DIR=$(readlink -f `dirname "${BASH_SOURCE[0]}"` | grep -o '.*/oshinko-release/test/e2e')
source $TEST_DIR/common

set_template oshinko-python-build-dc
set_git_uri https://github.com/radanalyticsio/s2i-integration-test-apps
get_templates

os::test::junit::declare_suite_start "$MY_SCRIPT"

echo "++ test_versions"
test_versions $S2I_TEST_IMAGE_PYSPARK

os::test::junit::declare_suite_end
