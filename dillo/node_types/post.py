node_type_post = {
    'name': 'dillo_post',
    'description': 'Dillo post type',
    'dyn_schema': {
        'post_type': {
            'type': 'string',
            'allowed': [
                'link',
                'text',
            ],
            'default': 'link',
        },
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'deleted',
                'flagged',
                'pending',
            ],
            'default': 'pending',
        },
        'shortcode': {
            # Alphanumeric ID
            'type': 'string',
            'maxlength': 6,
        },
        'slug': {
            'type': 'string',
        },
        'category': {
            # Categories are defined on the project level
            'type': 'string',
            'required': True
        },
        # Total count of positive ratings (updated at every rating action)
        'rating_positive': {
            'type': 'integer',
        },
        # Total count of negative ratings (updated at every rating action)
        'rating_negative': {
            'type': 'integer',
        },
        # Collection of ratings, keyed by user
        'ratings': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'user': {
                        'type': 'objectid'
                    },
                    'is_positive': {
                        'type': 'boolean'
                    },
                    # Weight of the rating based on user rep and the context.
                    # Currently we have the following weights:
                    # - 1 auto null
                    # - 2 manual null
                    # - 3 auto valid
                    # - 4 manual valid
                    'weight': {
                        'type': 'integer'
                    }
                }
            }
        },
        'hot': {'type': 'float'},
    },
    'form_schema': {
        'ratings': {'visible': False},
        'rating_positive': {'visible': False},
        'rating_negative': {'visible': False},
        'hot': {'visible': False},
    },
    'parent': []
}
