#!/bin/bash

TEST_DIR=$(readlink -f `dirname "${BASH_SOURCE[0]}"` | grep -o '.*/oshinko-release/test/e2e')
source $TEST_DIR/common

set_template oshinko-webui
get_templates

os::test::junit::declare_suite_start "$MY_SCRIPT"

echo "++ test_webui"
test_webui

os::test::junit::declare_suite_end
