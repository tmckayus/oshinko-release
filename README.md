# oshinko-release
This is a place to keep scripts related to creating oshinko releases

# Setting a tag on existing images on docker.io

To apply a new tag to existing images, use the `set_tag.sh` script followed by the `push_tag.sh` script.

```bash
$ ./set_tag.sh v0.3.1 stable
...
Images pulled and tagged successfully

$ ./push_tag.sh stable
...
Tagged images pushed successfully
```
# Testing released images

As part of a release, images should be tested to verify that
versions reported in logs match tags on the images, that
a simple app can be built and executed, and that the templates
created by https://radanalytics.io/resources.yaml can reference
those images.

To test images from a specific release:

```
$ S2I_TEST_OSHINKO_VERSION=v0.3.1 make test-release
```
This can be done for a new release (v0.3.1) before the *stable* tag
is moved to point to the new release.

To test images from the latest release tagged with *stable*:

```
$ S2I_TEST_STABLE=true S2I_TEST_OSHINKO_VERSION=v0.3.1 make test-release
```
This can be done after the *stable* tag has been moved to the new
release (v0.3.1).
