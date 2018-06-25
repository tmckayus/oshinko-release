#!/usr/bin/python2
import argparse
import getpass
import re
import requests
from time import sleep, time
import logging as log
from datetime import datetime

# github api v2 build status codes:
from github import Github, BadCredentialsException

API_ENDPOINT = 'https://api.github.com'

# Defaults
INTERVAL = 120
RETRIES = 30

WITH_VERBOSITY = log.DEBUG
WITHOUT_VERBOSITY = log.INFO

# All states for a github status
ERROR, FAILURE, PENDING, SUCCESS = "error", "failure", "pending", "success"

# Time to wait for ci builds to load for PR tests
PR_CONTEXT_LOAD_LENGTH = 10


def get_opts():
    parser = argparse.ArgumentParser(description='Make a PR and watch its statuses '
                                                 'and report success or failure. '
                                                 'Once it succeeds it will merge the PR')

    # Options for PR creation
    parser.add_argument('repo', metavar='REPO', type=str,
                        help='a github repo in the format user/repo')

    parser.add_argument('token', metavar='TOKEN', type=str, help='A github auth token')
    parser.add_argument('version', metavar='VER', type=str, help='oshinko version (eg. 0.5.2).')

    parser.add_argument('user', metavar='USER', type=str,
                        help='github user with permissions to create/merge a pr in the specified '
                             'repo, note that the token must be associated with this user')

    parser.add_argument('branch', metavar='BRANCH', type=str,
                        help='the base branch')

    # PR options
    parser.add_argument('-t', dest='title', default="[Release Bot] Release Update", type=str,
                        help='the title of the pr, by default a generic title is used')
    parser.add_argument('-b', dest='body', default="This PR is for a release update.", type=str,
                        help='the body of the pr, by default a generic body is used')
    parser.add_argument('-hd', dest='head', default="master", type=str,
                        help='the head of the pr, by default master head is used')
    # Watch options
    parser.add_argument('-i', dest='interval', default=[INTERVAL], type=int,
                        help='the length of the interval between each poll in seconds'
                             ' (Default {}).'.format(INTERVAL))
    parser.add_argument('-r', dest='retries', default=[RETRIES], type=int,
                        help='the maximum number of times github is '
                             'polled for build status updates (Default {}).'.format(RETRIES))
    parser.add_argument('-s', dest='contexts', default=[], type=str, nargs="+",
                        help='the contexts id to check for')

    # General options
    parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

    args = parser.parse_args()

    repo, token, version, gh_user, base_branch = \
        args.repo, args.token, args.version, args.user, args.branch
    pr_title, pr_body, pr_head = args.title, args.body, args.head
    verbose, interval, retries, contexts = args.verbose, args.interval, args.retries, args.contexts

    # Get logger
    loglevel = WITH_VERBOSITY if verbose else WITHOUT_VERBOSITY
    log.basicConfig(format='%(asctime)s - %(levelname)s:%(message)s', level=loglevel)
    log.getLogger('requests').setLevel(log.WARNING)

    validate(parser, repo, token)

    return repo, token, version, gh_user, interval, retries, \
           contexts, pr_title, pr_body, pr_head, base_branch


def validate(parser, repo, token):
    # Check repo syntax
    pattern = r'^\b\w+(?:-\w+)*[/]\w+(?:-\w+)*$$'
    if not re.match(pattern, repo):
        parser.error('A malformed repo was provided. Use -h for detailed usage instructions.')

    user, repo = repo.split('/')

    # Check if repo exist
    head = {'Authorization': 'token {}'.format(token)}
    r = requests.get('{}/repos/{}/{}'.format(API_ENDPOINT, user, repo), headers=head)
    if r.status_code >= 400:
        parser.error('Repo not found, ensure the repo supplied is wellformed and exists: '
                     '<user>/<repo>')

    data = r.json()
    log.info('Found repo: {}/{}, Description: {}'.format(data['owner']['login'], data['name'],
                                                         data['description']))

    # Check token syntax
    if re.search(r'[^A-z0-9-]', token):
        parser.error('Token is malformed, please provide a proper token.')


# Specify owner if owner != logged in user
def get_repo(user, repo_name, token, owner=None):
    if token:
        github = Github(user, token)
    else:
        github = Github(user, getpass.getpass())

    try:
        if owner is None:
            repo = github.get_user(user).get_repo(repo_name)
        else:
            repo = github.get_user(owner).get_repo(repo_name)
    except BadCredentialsException:
        error_msg = 'Bad Github credentials. Ensure a valid user and password/token are provided.'
        log.error(error_msg)
        raise BadCredentialsException

    return repo


# Only retrieve the statuses that are created after the PR is created
def get_status(statuses_url, time_pr_created, token):
    # Authorized requests give a higher api rate limit
    # To reduce chances of hitting rate limit, use longer intervals
    head = {'Authorization': 'token {}'.format(token)}
    r = requests.get(statuses_url, headers=head)
    statuses = r.json()

    if r.status_code >= 400:
        log.error('Statuses could not be reached. Ensure the Github rate-limit was not reached.')
        exit(1)

    if not statuses:
        log.error('No success events found within statuses_url.')
        exit(1)

    date_format = '%Y-%m-%dT%H:%M:%SZ'
    statuses = filter(lambda status:
                      datetime.strptime(status['created_at'], date_format) > time_pr_created,
                      statuses)

    return statuses


def create_pr(gh_user, repo_name, token, owner, title, head, base, body):
    repo = get_repo(gh_user, repo_name, token, owner=owner)
    pull = repo.create_pull(title=title, head=head, base=base, body=body)
    url = pull.url
    log.info('Pull {} successfully created, see details at: {}'.format(pull.number, url))
    return pull


def watch_pr_statuses(pull, contexts, interval, retries, time_pr_created, token):
    # Wait for PR notifications for contexts to begin builds
    log.info('Waiting {} seconds for the contexts to show up.'.format(PR_CONTEXT_LOAD_LENGTH))
    sleep(PR_CONTEXT_LOAD_LENGTH)

    statuses_url = pull.raw_data['statuses_url']

    # Loop through all the statuses to ensure that each context has passed
    contexts_succeeded = []
    contexts_queue = contexts[:]
    all_contexts_succeeded = False
    log.info("Polling github for status updates every {} seconds for a maximum of {} times..."
             .format(interval, retries))
    retries_left = retries
    while not all_contexts_succeeded and retries_left > 0:
        log.info("Polling github for statuses on PR {}, attempt # {}"
                 .format(pull.number, retries - retries_left + 1))
        statuses = get_status(statuses_url, time_pr_created, token)
        for status in statuses:
            context_found, state_found = status['context'], status['state']

            # Only concerned with context's we're watching
            if context_found not in contexts_queue:
                continue

            if state_found == FAILURE or state_found == ERROR:
                log.error('The context: {}, was found to be in state: {}, exiting.'
                          .format(context_found, state_found))
                exit(1)

            # Add to the pool of succeeded contexts
            if state_found == SUCCESS and context_found not in contexts_succeeded:
                log.info('The context: {} was successful.'.format(context_found))
                contexts_succeeded.append(context_found)
                contexts_queue.remove(context_found)

        if len(contexts_succeeded) == len(contexts):
            all_contexts_succeeded = True
        else:
            sleep(interval)
            retries_left -= 1

    if not all_contexts_succeeded:
        log.error('One of the contexts was not in success state. No merge initiated.')
        exit(1)

    return 0


def merge_pr(pull):
    pr_merge_status = pull.merge().merged
    if pr_merge_status:
        log.info('Merge action performed successfully.')
    else:
        log.error('Merge failed, exiting.')
        exit(1)


def main():
    repo, token, version, gh_user, interval, retries, contexts, title, body, head, base = get_opts()
    owner, repo_name = repo.split('/')

    # Create PR
    pull = create_pr(gh_user, repo_name, token, owner, title, head, base, body)
    time_pr_created = datetime.utcnow()

    if not contexts:
        log.info('No contexts provided to watch, exiting.')
        return

    watch_failed = watch_pr_statuses(pull, contexts, interval, retries, time_pr_created, token)

    if watch_failed:
        log.error('A problem was encountered. The watch ended unsuccessfully.')
    else:
        log.info('All context jobs succeeded. Performing merge.')

    merge_pr(pull)

    return


if __name__ == "__main__":
    main()
