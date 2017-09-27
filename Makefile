S2I_TEST_IMAGE_PYSPARK = radanalyticsio/radanalytics-pyspark
S2I_TEST_IMAGE_JAVA = radanalyticsio/radanalytics-java-spark
S2I_TEST_IMAGE_SCALA = radanalyticsio/radanalytics-scala-spark
S2I_TEST_STABLE = false

export S2I_TEST_IMAGE_PYSPARK
export S2I_TEST_IMAGE_JAVA
export S2I_TEST_IMAGE_SCALA
export S2I_TEST_STABLE

test-release:
	test/e2e/run.sh

.PHONY: test-release
