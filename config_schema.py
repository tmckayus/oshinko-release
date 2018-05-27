schema = {
    'tag_name': {
        'required': True,
        'type': 'string'
    },
    'target_commitish': {
        'required': True,
        'type': 'string'
    },
    'name': {
        'required': True,
        'type': 'string'
    },
    'body': {
        'required': True,
        'type': 'string'
    },
    'draft': {
        'required': True,
        'type': 'boolean'
    },
    'prerelease': {
        'required': True,
        'type': 'boolean'
    },
    'assets': {
        'required': False,
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                "Content-Type": {'type': 'string', 'required': True},
                "name": {'type': 'string', 'required': True},
                "label": {'type': 'string', 'required': True}
            }
        }
    }
}
