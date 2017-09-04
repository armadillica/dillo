"""PATCH support for comment nodes."""

import logging

from flask import abort, current_app
from pillar.api.utils import authentication, jsonify
from pillar.api.nodes.custom import register_patch_handler
from pillar.api.nodes.custom.comment import vote_comment, assert_is_valid_patch

from dillo.posts.eve_hooks import algolia_index_post_save

log = logging.getLogger(__name__)
COMMENT_VOTING_OPS = {'upvote', 'downvote', 'revoke'}


@register_patch_handler('dillo_post')
def patch_post(node_id, patch):
    assert_is_valid_patch(node_id, patch)
    user_id = authentication.current_user_id()

    nodes_coll = current_app.data.driver.db['nodes']
    node_user_id = nodes_coll.find_one({'_id': node_id },
                                       projection={'user': 1})

    # we don't allow the user to down/upvote their own posts.
    if user_id == node_user_id:
        return abort(403)

    if patch['op'] in COMMENT_VOTING_OPS:
        result, node = vote_comment(user_id, node_id, patch)
        # Fetch the full node for reindexing
        # TODO (can be improved by making a partial update)
        nodes_coll = current_app.db()['nodes']
        node = nodes_coll.find_one({'_id': node['_id']})
        algolia_index_post_save(node)
    else:
        return abort(403)

    return jsonify({'_status': 'OK',
                    'result': result,
                    'properties': node['properties']
                    })
