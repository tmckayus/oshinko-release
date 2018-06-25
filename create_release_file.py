#!/usr/bin/python2
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
import os
import argparse
import magic


def get_opts():
    parser = argparse.ArgumentParser(description='Create a release yaml file for consumption '
                                                 'by git_release script.')

    parser.add_argument('body', metavar='BODY', type=str, default=None,
                        help='a release notes .md file.')

    parser.add_argument('version', metavar='VER', type=str, default=None,
                        help='oshinko version (eg. 0.5.2).')

    parser.add_argument('destination', metavar='DEST', type=str, default=None,
                        help='destination path of where the release file generated '
                             '(e.g. /etc/file.yaml.')

    # Optionals
    parser.add_argument('-t', dest='tag_name', type=str, default=None,
                        help='tag name for this release, auto generated `v{$VERSION}` by default.')

    parser.add_argument('-n', dest='name', type=str, default=None,
                        help='name for this release, auto generated '
                             '`version {$VERSION}` by default.')

    parser.add_argument('-tc', dest='target_commit', type=str, default='master',
                        help='target commit for this release, master by default.')

    parser.add_argument('-d', dest='draft', action='store_true', help='sets draft to true')

    parser.add_argument('-pr', dest='prerelease', action='store_true',
                        help='sets this release as a prerelease if specified.')

    parser.add_argument('-a', dest='assets', type=str, default=None,
                        help='path to dir containing asset files for this release, note all files '
                             'in this directory will be used as asset files so ensure only assets '
                             'exist in this directory.')

    args = parser.parse_args()
    version = args.version
    body = args.body

    # optionals
    tag_name = args.tag_name
    name = args.name
    target_commit = args.target_commit
    draft = args.draft
    prerelease = args.prerelease
    assets = args.assets
    destination = args.destination

    return version, body, tag_name, name, target_commit, draft, prerelease, assets, destination


def main():
    version, body, tag_name, name, target_commit, draft, prerelease, asset_path, dest = get_opts()

    tag_name = 'v{}'.format(version) if not tag_name else tag_name
    name = 'version {}'.format(version) if not name else name

    yaml = YAML()
    yaml.indent(mapping=1)

    data = CommentedMap()

    with open(body, 'r') as notes:
        notes_read = notes.read()
        data['tag_name'] = tag_name
        data['target_commitish'] = target_commit
        data['name'] = name
        data['body'] = notes_read
        data['draft'] = draft
        data['prerelease'] = prerelease

    if asset_path:
        mime = magic.Magic(mime=True)
        data['assets'] = []

        for asset in os.listdir(asset_path):
            abs_path = os.path.join(asset_path, asset)
            asset_map = CommentedMap()
            content_type = mime.from_file(abs_path)
            label = os.path.basename(asset)

            asset_map['Content-Type'] = content_type
            asset_map['name'] = abs_path
            asset_map['label'] = label

            data['assets'].append(asset_map)

    with open(dest, 'w') as dest:
        yaml.dump(data, dest)


if __name__ == "__main__":
    main()

