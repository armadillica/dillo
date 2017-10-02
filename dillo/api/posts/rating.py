"""PATCH support for comment nodes."""

import logging

from flask import abort, current_app
from pillar.api.utils import authentication, jsonify
from pillar.api.nodes.custom import register_patch_handler
from pillar.api.nodes.custom.comment import vote_comment, assert_is_valid_patch

from dillo.api.posts.hooks import algolia_index_post_save, update_hot
from dillo import EXTENSION_NAME

log = logging.getLogger(__name__)
COMMENT_VOTING_OPS = {'upvote', 'downvote', 'revoke'}
POST_VOTE_WEIGHT = 5


def rating_difference(node):
    return node['properties']['rating_positive'] - node['properties']['rating_negative']


@register_patch_handler('dillo_post')
def patch_post(node_id, patch):
    assert_is_valid_patch(node_id, patch)
    user_id = authentication.current_user_id()

    if patch['op'] in COMMENT_VOTING_OPS:
        nodes_coll = current_app.db()['nodes']
        node = nodes_coll.find_one({'_id': node_id})

        old_rating = rating_difference(node)
        result, node = vote_comment(user_id, node_id, patch)
        new_rating = rating_difference(node)

        # Update the user karma based on the rating differences.
        karma_increase = (new_rating - old_rating) * POST_VOTE_WEIGHT
        if karma_increase != 0:
            node_user_id = nodes_coll.find_one(
                {'_id': node_id},
                projection={
                    'user': 1,
                })['user']

            users_collection = current_app.db()['users']
            db_fieldname = f'extension_props.{EXTENSION_NAME}.karma'

            users_collection.find_one_and_update(
                {'_id': node_user_id},
                {'$inc': {db_fieldname: karma_increase}},
                {db_fieldname: 1},
            )

        # Fetch the full node for updating hotness and reindexing
        # TODO (can be improved by making a partial update)
        node = nodes_coll.find_one({'_id': node['_id']})
        update_hot(node)
        nodes_coll.update_one({'_id': node['_id']}, {'$set': {'properties.hot': node['properties']['hot']}})

        algolia_index_post_save(node)
    else:
        return abort(403)

    return jsonify({'_status': 'OK',
                    'result': result,
                    'properties': node['properties']
                    })


def rebuild_karma():
    """Re-calculate users karma

    It also initialize the ['extension_props]['karma'] if needed.
    """
    db = current_app.db()
    users_collection = db['users'].find({'_deleted': {'$ne': True}})
    db_fieldname = f'extension_props.{EXTENSION_NAME}.karma'

    for user in users_collection:
        posts_collection = db['nodes'].find({
            'node_type': 'dillo_post',
            'user': user['_id'],
        })

        karma = 0
        for post in posts_collection:
            karma += rating_difference(post) * POST_VOTE_WEIGHT

        db['users'].find_one_and_update(
            {'_id': user['_id']},
            {'$set': {db_fieldname: karma}},
            {db_fieldname: 1},
        )
