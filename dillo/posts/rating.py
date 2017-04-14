"""PATCH support for comment nodes."""

import logging

from flask import abort
from pillar.api.utils import authentication, jsonify
from pillar.api.nodes.custom import register_patch_handler
from pillar.api.nodes.custom.comment import vote_comment, assert_is_valid_patch

log = logging.getLogger(__name__)
COMMENT_VOTING_OPS = {'upvote', 'downvote', 'revoke'}


@register_patch_handler('dillo_post')
def patch_post(node_id, patch):
    assert_is_valid_patch(node_id, patch)
    user_id = authentication.current_user_id()

    if patch['op'] in COMMENT_VOTING_OPS:
        result, node = vote_comment(user_id, node_id, patch)
    else:
        return abort(403)

    return jsonify({'_status': 'OK',
                    'result': result,
                    'properties': node['properties']
                    })
