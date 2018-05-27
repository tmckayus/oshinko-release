#!/usr/bin/python2
import re
import requests
import argparse
from ruamel.yaml import YAML
import logging as log
from cerberus import Validator
from config_schema import schema
import json
from github import Github, BadCredentialsException, UnknownObjectException
import getpass
import sys
from os import path

API_ENDPOINT = 'https://api.github.com'


def get_opts():
    parser = argparse.ArgumentParser(description='Automate release procedure on github.')
    parser.add_argument('repo', metavar='R', type=str, nargs=1,
                        help='a github repo in the format user/repo or org/repo')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', dest='config', type=str, default=None, nargs=1,
                       help='create a release, requires configuration file.')

    group.add_argument('-d', dest='tag', type=str, default=None, nargs=1,
                       help='delete a release, requires a tag name.')

    parser.add_argument('-a', dest='token', type=str, default=None, nargs=1,
                        help='a git hub auth token. Skips user input for authentication if '
                             'provided.')

    parser.add_argument('-t', dest='deletetag', help='Delete tag with release, [-d] must be '
                                   'specified.', action='store_true')

    args = parser.parse_args()
    token = args.token[0] if args.token else None
    conf = args.config[0] if args.config else None
    tag = args.tag[0] if args.tag else None
    delete_tag = args.deletetag

    if delete_tag and not tag:
        parser.error('[-t] requires a release tag to be specified via [-d].')

    repo = args.repo[0]

    loglevel = log.INFO
    log.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=loglevel)
    log.getLogger('requests').setLevel(log.WARNING)

    if conf:
        validate_yaml(parser, conf)

    validate_repo(parser, repo)

    user, repo_name = repo.split('/')

    return user, repo_name, conf, token, tag, delete_tag


def validate_repo(parser, repo):
    # Check repo syntax
    pattern = r'^\b\w+(?:-\w+)*[/]\w+(?:-\w+)*$$'
    if not re.match(pattern, repo):
        parser.error('A malformed repo was provided. Use -h for detailed usage instructions.')

    user, repo = repo.split('/')

    # Check if repo exist
    r = requests.get('{}/repos/{}/{}'.format(API_ENDPOINT, user, repo))
    if r.status_code >= 400:
        parser.error('Unable to reach repo, ensure the repo supplied is wellformed and exists:'
                     '<user>/<repo>')
    return True


def validate_yaml(parser, conf):
    # Ensure file is formatted correctly
    yaml = YAML()
    with open(conf, 'r') as config:
        conf_yaml = yaml.load(config)
        # cerberus works better on a dict; a simple way to convert yaml -> python dict:
        conf_dict = json.loads(json.dumps(conf_yaml))

    v = Validator(schema)
    is_valid = v.validate(conf_dict, schema)
    if not is_valid:
        raise parser.error('Invalid file format in file {}\nError: {}'.format(conf, v.errors))

    assets = conf_dict['assets']
    for asset in assets:
        if not path.exists(asset['name']):
            raise parser.error('File {} specified for asset with label {} does not exist.'
                               .format(asset['label'], asset['name']))

    return is_valid


def create_release(conf, repo, user, repo_name):
    yaml = YAML()
    with open(conf, 'r') as config:
        conf_yaml = yaml.load(config)

    r = requests.get('{}/repos/{}/{}/releases/tags/{}'.format(API_ENDPOINT, user,
                                                              repo_name, conf_yaml['tag_name']))
    if r.status_code == 200:
        log.error('Repo already exists.')
        sys.exit(1)

    log.info('Creating a git release with tag {}.'.format(conf_yaml['tag_name']))
    repo.create_git_release(conf_yaml['tag_name'], conf_yaml['name'], conf_yaml['body'],
                            conf_yaml['draft'], conf_yaml['prerelease'],
                            conf_yaml['target_commitish'])

    release = repo.get_release(conf_yaml['tag_name'])

    log.info('Uploading assets...')
    for asset in conf_yaml['assets']:
        release.upload_asset(
            asset['name'],
            asset['label'],
            asset['Content-Type']
        )
        log.info('Asset {} uploaded successfully.'.format(asset['label']))
    log.info('Release successfully created.')


def delete_release(tag, delete_tag, repo):
    log.info('Deleting a git release with tag {}.'.format(tag))

    try:
        release = repo.get_release(tag)
        release.delete_release()
    except UnknownObjectException:
        log.error('Release with tag {} was not found.'.format(tag))
        sys.exit(1)

    if delete_tag:
        log.info('Deleting a git tag {}.'.format(tag))
        repo.get_git_ref(ref='tags/'+tag).delete()


def main():
    user, repo_name, conf, token, tag, delete_tag = get_opts()

    if token:
        github = Github(user, token)
    else:
        github = Github(user, getpass.getpass())

    try:
        repo = github.get_user(user).get_repo(repo_name)
    except BadCredentialsException:
        log.error('Bad credentials. Ensure a valid user and password/token are provided.')
        sys.exit(1)

    if conf:
        create_release(conf, repo, user, repo_name)
    else:
        delete_release(tag, delete_tag, repo)

    return 0


main()
