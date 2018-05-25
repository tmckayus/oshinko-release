import argparse
import re
import requests
from sys import exit
from time import sleep
import logging as log

# Docker api v2 build status codes:
SUCCESS, QUEUED, CANCELLED = 10, 0, -4

STATUS_CODES = {
    10: 'SUCCESS',
    3: 'BUILDING',
    2: 'BUILDING',
    1: 'QUEUED',
    0: 'QUEUED',
    -1: 'ERROR',
    -2: 'ERROR',
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

    args = parser.parse_args()
    repo, token, interval, retries, force, verbose = \
        args.repo[0], args.token[0], args.interval[0], args.retries[0], args.force, args.verbose

    loglevel = WITH_VERBOSITY if verbose else WITHOUT_VERBOSITY
    log.basicConfig(format='%(asctime)s - %(levelname)s:%(message)s', level=loglevel)
    log.getLogger('requests').setLevel(log.WARNING)

    validate(parser, repo, token)

    return repo, token, interval, retries, force


def validate(parser, repo, token):
    # Check repo syntax
    if re.search(r'^/|[^A-z0-9-/]|/$|/{2,}', repo):
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


def fetch_build(user, repo):
    r = requests.get('{}/repositories/{}/{}/buildhistory/?page_size=1'
                     .format(V2_ENDPOINT, user, repo))
    data = r.json()
    build = data['results'][0]

    return int(build['status']), build['build_code']


def trigger_build(user, repo, token):
    r = requests.post('{}/u/{}/{}/trigger/{}/'.format(REGISTRY_ENDPOINT, user, repo, token))

    if r.status_code != 200:
        raise RuntimeError('Trigger request failed. Received status code:{}. '
                           'Ensure the token is correct.'.format(r.status_code))

    # Allot time for request to go through
    sleep(5)
    return r.status_code == 200


def main():
    repo, token, interval, retries, force = get_opts()
    user, repo = repo.split('/')

    # Get most recent build details
    status, build_code = fetch_build(user, repo)

    if status == SUCCESS or status < QUEUED:
        if not force:
            state = 'success' if status == SUCCESS else 'stalled'
            log.warn('The latest build is in a {} state. Nothing to watch. '
                     'Use -f to force a trigger. Exiting.'.format(state))
            return 0
        else:
            log.info('No autobuilds in progress. Initiating a new trigger (-f).')
            trigger_build(user, repo, token)
            status, build_code = fetch_build(user, repo)

    log.info('Polling dockerhub every {} seconds for a maximum of {} polls...'
             .format(interval, retries))
    log.debug('Watching build: {}, status: {}'.format(build_code, status_lookup(status)))

    while status != SUCCESS and retries > 0:
        retrigger = False

        # build is in an error/cancelled state
        if status < QUEUED:
            if status == CANCELLED:
                log.warn('The build was cancelled via an external source. The script will '
                         'continue attempting build triggers until success/timeout.')

            log.info('Build is in stalled/error state. Triggering a new build.')
            trigger_build(user, repo, token)
            retrigger = True

        sleep(interval)
        status, new_build_code = fetch_build(user, repo)
        log.debug('Watching build: {}, status: {}'.format(new_build_code, status_lookup(status)))

        # A new build was not created
        if retrigger and build_code == new_build_code:
            raise RuntimeError('Failed to retrieve triggered build. ')

        build_code = new_build_code
        retries -= 1

    if status != SUCCESS:
        log.warn('Retry timeout reached while polling build:{}, last known status: {}({})'
                 .format(build_code, status_lookup(status), status))
        exit(1)
    else:
        log.info('Build: {} successfully completed. Status: {}({})'
                 .format(build_code, status_lookup(status), status))


main()
