#!/usr/bin/python2
import argparse
import re
import requests
from time import sleep
import logging as log
import json

# Docker api v2 build status codes:
SUCCESS, QUEUED, CANCELLED = 10, 0, -4

STATUS_CODES = {
    10: 'SUCCESS',
    3: 'BUILDING', 2: 'BUILDING',
    1: 'QUEUED', 0: 'QUEUED',
    -1: 'ERROR', -2: 'ERROR',
    -4: 'CANCELLED'
}

V2_ENDPOINT = 'https://hub.docker.com/v2'
REGISTRY_ENDPOINT = 'https://registry.hub.docker.com'

# Defaults
INTERVAL = 120
RETRIES = 30

WITH_VERBOSITY = log.DEBUG
WITHOUT_VERBOSITY = log.INFO


def get_opts():
    parser = argparse.ArgumentParser(description='Watch a dockerhub repo autobuild.')

    parser.add_argument('repo', metavar='R', type=str, nargs=1,
                        help='a dockerhub repo in the format user/repo')

    parser.add_argument('token', metavar='T', type=str, nargs=1, help='A dockerhub trigger token')

    parser.add_argument('-f', '--force', dest='force', action='store_true',
                        help='force trigger a build even if the last build is in a '
                             'success or stalled state.')

    parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

    parser.add_argument('-i', dest='interval', default=[INTERVAL], type=int, nargs=1,
                        help='the length of the interval between each poll in seconds'
                             ' (Default {}).'.format(INTERVAL))

    parser.add_argument('-r', dest='retries', default=[RETRIES], type=int, nargs=1,
                        help='the maximum number of times dockerhub is '
                             'polled for build status updates (Default {}).'.format(RETRIES))

    parser.add_argument('-t', metavar='Tag', dest='tags', default=[], type=str, nargs="+",
                        help='supply the tag source from which the build was created, to watch.')

    parser.add_argument('-b', metavar='Branch', dest='branches', default=[], type=str, nargs="+",
                        help='supply the branch source from which the build was created, to watch.')

    args = parser.parse_args()

    tags = args.tags
    branches = args.branches
    docker_tags = []
    for tag in tags:
        meta_info = {
            "source_type": "Tag",
            "sourceref": tag,
            "docker_tag": tag
        }
        docker_tags.append(meta_info)

    for branch in branches:
        meta_info = {
            "source_type": "Branch",
            "sourceref": branch,
            "docker_tag": "{}-latest".format(branch)
        }
        docker_tags.append(meta_info)

    repo, token, interval, retries, force, verbose = \
        args.repo[0], args.token[0], args.interval[0], args.retries[0], \
        args.force, args.verbose

    loglevel = WITH_VERBOSITY if verbose else WITHOUT_VERBOSITY
    log.basicConfig(format='%(asctime)s - %(levelname)s:%(message)s', level=loglevel)
    log.getLogger('requests').setLevel(log.WARNING)

    validate(parser, repo, token)

    return repo, token, interval, retries, force, docker_tags


def validate(parser, repo, token):
    # Check repo syntax
    pattern = r'^\b\w+(?:-\w+)*[/]\w+(?:-\w+)*$$'
    if not re.match(pattern, repo):
        parser.error('A malformed repo was provided. Use -h for detailed usage instructions.')

    user, repo = repo.split('/')

    # Check if repo exist
    r = requests.get('{}/repositories/{}/{}'.format(V2_ENDPOINT, user, repo))
    if r.status_code >= 400:
        parser.error('Repo not found, ensure the repo supplied is wellformed and exists: '
                     '<user>/<repo>')

    data = r.json()
    log.info('Found repo: {}/{}, Description: {}'.format(data['user'], data['name'],
                                                         data['description']))

    # Check token syntax
    if re.search(r'[^A-z0-9-]', token):
        parser.error('Token is malformed, please provide a proper token.')


def status_lookup(code):
    if code not in STATUS_CODES:
        return 'UNKNOWN({})'.format(code)
    return STATUS_CODES[code]


def fetch_build_latest(user, repo):
    r = requests.get('{}/repositories/{}/{}/buildhistory/?page_size=1'
                     .format(V2_ENDPOINT, user, repo))
    data = r.json()
    if not data['results']:
        log.error('This repo does not have any builds in its history to watch')
        raise RuntimeError('Repo {} does not have any builds in its history to watch'.format(repo))
    build = data['results'][0]
    return build


# Finds builds that match the provided tags
# Only the most recent matches are returned if more than one are found.
def fetch_builds(tags_original, user, repo, page_size):
    endpoint = '{}/repositories/{}/{}/buildhistory/?page_size={}' \
        .format(V2_ENDPOINT, user, repo, page_size)

    r = requests.get(endpoint)
    data = r.json()

    builds_retrieved = data['results']
    builds_matched = []
    tags = tags_original[:]
    for i, build in enumerate(builds_retrieved):
        i = 0
        while i < len(tags) and tags:
            if build['dockertag_name'] == tags[i]['docker_tag']:
                build['source_info'] = tags[i]
                builds_matched.append(build)
                del tags[i]
            i += 1
    return builds_matched


def trigger_build(user, repo, build, token, force=False):
    if build['status'] == CANCELLED:
        log.warn('The build was cancelled via an external source. The script will '
                 'continue attempting build triggers until success/timeout.')

    if force:
        log.info('Force initiating a new trigger (-f) for build {}.'.format(build['build_code']))
    else:
        log.info('Build is in stalled/error state. Triggering a new build.')

    # Source info is only required if we're watching based off given source tags/builds
    # (Since dockerhub api does not provide source info of a build)
    # Otherwise we're simply watching the latest build and source data is not relevant
    if "source_info" in build:
        source_info = build['source_info']
        data = {"source_type": source_info['source_type'], "source_name": source_info['sourceref']}
        endpoint = '{}/u/{}/{}/trigger/{}/'.format(REGISTRY_ENDPOINT, user, repo, token)
        headers = {'Content-type': 'application/json'}
        r = requests.post(endpoint, headers=headers, data=json.dumps(data))
    else:
        endpoint = '{}/u/{}/{}/trigger/{}/'.format(REGISTRY_ENDPOINT, user, repo, token)
        r = requests.post(endpoint)

    if r.status_code != 200:
        raise RuntimeError('Trigger request failed. Received status code:{}. '
                           'Ensure the token is correct.'.format(r.status_code))

    # Allot time for request to go through
    sleep(5)
    return r.status_code == 200


def watch_build(repo, token, interval, retries, force, tags):
    user, repo = repo.split('/')

    builds_to_watch = fetch_builds(tags, user, repo, 200) \
        if len(tags) > 0 else [fetch_build_latest(user, repo)]

    if not builds_to_watch:
        log.error('Could not find any builds.')
        raise RuntimeError('Repo {} does not have any builds in its history to watch'.format(repo))

    # Check if the builds_to_watch are all in a non-success state
    # If they are not in a BUILDING or QUEUED state we only proceed if [-f] is supplied
    initial_builds_to_trigger = []
    for build in builds_to_watch:
        status, build_code = build['status'], build['build_code']
        if status == SUCCESS or status < QUEUED:
            if not force:
                state = 'success' if status == SUCCESS else 'stalled'
                error_msg = 'The build [{}] is in a {} state. Nothing to watch. Use -f to ' \
                            'force a trigger. Exiting.'.format(build_code, state)
                log.error(error_msg)
                raise RuntimeError(error_msg)

            else:
                initial_builds_to_trigger.append(build)

    for build in initial_builds_to_trigger:
        trigger_build(user, repo, build, token, force=force)

    # If builds were triggered, update build information
    if initial_builds_to_trigger:
        builds_to_watch = fetch_builds(tags, user, repo, 200) \
            if len(tags) > 0 else [fetch_build_latest(user, repo)]

    log.info('Polling dockerhub every {} seconds for a maximum of {} polls...'
             .format(interval, retries))

    for build in builds_to_watch:
        status, build_code = build['status'], build['build_code']
        log.debug('Watching build: {}, status: {}'.format(build_code, status_lookup(status)))

    all_builds_succeeded = False
    while not all_builds_succeeded and retries > 0:
        # If one of the builds is successful, remove from watch list
        new_builds_to_watch, builds_to_trigger, builds_in_process = [], [], []
        for build in builds_to_watch:
            status = build['status']
            if status != SUCCESS:
                new_builds_to_watch.append(build)
                if status < QUEUED:
                    builds_to_trigger.append(build)
                else:
                    builds_in_process.append(build)

        builds_to_watch = new_builds_to_watch

        # There is no point in triggering a new build if one is already queued/building
        if not builds_in_process and builds_to_trigger:
            trigger_build(user, repo, builds_to_trigger[0], token, force=True)

        # TODO: Set log level check conditions, ignore loops if not debug
        for b in builds_to_trigger:
            log.debug("Builds to trigger: {}, code: {}".format(b['status'], b['build_code']))

        for b in builds_in_process:
            log.debug("Builds in process: {}, code: {}".format(b['status'], b['build_code']))

        for b in builds_to_watch:
            log.debug("Builds to watch: {}, code: {}".format(b['status'], b['build_code']))

        # If no builds to watch we're done
        if builds_to_watch:
            sleep(interval)
            builds_to_watch = fetch_builds(tags, user, repo, 200) \
                if len(tags) > 0 else [fetch_build_latest(user, repo)]
        else:
            all_builds_succeeded = True

        retries -= 1

    if not all_builds_succeeded:
        error_msg = 'All builds were not successfully completed.'
        log.warn(error_msg)
        RuntimeError(error_msg)
    else:
        log.info('All builds successfully completed.')


def main():
    repo, token, interval, retries, force, tags = get_opts()
    watch_build(repo, token, interval, retries, force, tags)


if __name__ == "__main__":
    main()