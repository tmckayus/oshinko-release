#!/usr/bin/python2
from github import Github, BadCredentialsException, UnknownObjectException
from cerberus import Validator
from config_schema import schema
from ruamel.yaml import YAML
import os
import re
import tempfile
import requests
import argparse
import logging as log
import json
import getpass
import hashlib
import ntpath
import magic


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

    parser.add_argument('-u', dest='gh_user', type=str, default=None, nargs=1,
                        help='if the user creating the release is different than the repo owner, '
                             'specify their github username here, note that any token provided '
                             'should be assigned to this username.')

    parser.add_argument('-t', dest='deletetag', help='Delete tag with release, [-d] must be '
                                                     'specified.', action='store_true')

    args = parser.parse_args()
    token = args.token[0] if args.token else None
    conf = args.config[0] if args.config else None
    tag = args.tag[0] if args.tag else None
    delete_tag = args.deletetag
    gh_user = args.gh_user[0]

    if delete_tag and not tag:
        parser.error('[-t] requires a release tag to be specified via [-d].')

    repo = args.repo[0]

    loglevel = log.INFO
    log.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=loglevel)
    log.getLogger('requests').setLevel(log.WARNING)

    if conf:
        validate_yaml(parser, conf)

    validate_repo(parser, repo)

    owner, repo_name = repo.split('/')

    return owner, repo_name, conf, token, tag, delete_tag, gh_user


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

    if 'assets' in conf_dict:
        assets = conf_dict['assets']
        for asset in assets:
            if not os.path.exists(asset['name']):
                raise parser.error('File {} specified for asset with label {} does not exist.'
                                   .format(asset['label'], asset['name']))

    return is_valid


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


def create_checksum_text(assets):
    checksum_data = ''
    for asset in assets:
        checksum = sha256_checksum(asset['name'])
        checksum_data += '{} *{}\n'.format(checksum, path_leaf(asset['name']))
    return checksum_data


# Securely create a temporary checksum asset to uplaod and remove afterwards
def upload_checksum(data, release, tmpdir):
    filename = 'SHA256-CHECKSUM'
    created_new_dir = False
    saved_umask = None
    if not tmpdir:
        tmpdir = tempfile.mkdtemp()
        # Ensure the file is read/write by the creator only
        saved_umask = os.umask(0o077)
        created_new_dir = True

    path = os.path.join(tmpdir, filename)
    try:
        with open(path, "w") as tmp:
            tmp.write(data)
            tmp.flush()
            release.upload_asset(
                path,
                filename,
                'plain'
            )
            log.info('Asset {} uploaded successfully.'.format(filename))
            os.remove(path)
    except IOError:
        log.error('Error while writing CHECKSUM')
        raise IOError('Error while writing CHECKSUM')
    finally:
        if created_new_dir:
            os.umask(saved_umask)
            os.rmdir(tmpdir)


# TODO: Add verification release was uploaded successfully
def create_release(repo, tag_name, name, body, draft, prerelease,
                   target_commitish, assets=None, tmpdir=''):
    if assets is None:
        assets = []

    log.info('Creating a git release with tag {}.'.format(tag_name))
    repo.create_git_release(tag_name, name, body, draft, prerelease, target_commitish)

    if assets:
        release = repo.get_release(tag_name)
        checksum_data = create_checksum_text(assets)

        log.info('Uploading assets...')
        for asset in assets:
            release.upload_asset(
                asset['name'],
                asset['label'],
                asset['Content-Type']
            )
            log.info('Asset {} uploaded successfully.'.format(asset['label']))
        upload_checksum(checksum_data, release, tmpdir)

        log.info('Release successfully created.')


def delete_release(tag, delete_tag, repo):
    log.info('Deleting a git release with tag {}.'.format(tag))

    try:
        release = repo.get_release(tag)
        release.delete_release()
    except UnknownObjectException:
        log.error('Release with tag {} was not found.'.format(tag))
        raise UnknownObjectException

    if delete_tag:
        log.info('Deleting a git tag {}.'.format(tag))
        repo.get_git_ref(ref='tags/'+tag).delete()


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


def main():
    owner, repo_name, conf, token, tag, delete_tag, gh_user = get_opts()

    # If a separate gh_user is not provided, owner is assumed as the user performing release
    if gh_user is None:
        gh_user = owner

    repo = get_repo(gh_user, repo_name, token, owner)

    if conf:
        yaml = YAML()
        with open(conf, 'r') as config:
            conf_yaml = yaml.load(config)

        tag_name, name, body, draft, prerelease, target_commitish = \
            conf_yaml['tag_name'], conf_yaml['name'], conf_yaml['body'], \
            conf_yaml['draft'], conf_yaml['prerelease'], \
            conf_yaml['target_commitish']

        assets = conf_yaml['assets'] if 'assets' in conf_yaml else []
        create_release(repo, tag_name, name, body, draft, prerelease, target_commitish, assets)
    else:
        delete_release(tag, delete_tag, repo)

    return 0


if __name__ == "__main__":
    main()

