import logging

import flask

from pillar.api.nodes import only_for_node_type_decorator
import pillar.api.activities
import pillar.api.utils.authentication

from dillo.api.posts.hooks import algolia_index_post_save

log = logging.getLogger(__name__)

comment_nodes_only = only_for_node_type_decorator('comment')


def get_parent_post(node):
    """Given a comment node, find it's parent post.

    If the comment is a reply to a comment, find the parent post of
    such comment.
    """
    parent_id = node.get('parent', None)

    if not parent_id:
        raise ValueError('Node %s has no parent.' % node['_id'])

    db = flask.current_app.db()
    parent = db['nodes'].find_one({'_id': parent_id},
                                  projection={'node_type': 1, 'parent': 1})
    if parent['node_type'] == 'dillo_post':
        p = db['nodes'].find_one({'_id': parent['_id']})
        return p
    else:
        return get_parent_post(parent)


@comment_nodes_only
def reindex_post(comment):
    """Reindex the post, while updating the comments count."""
    post = get_parent_post(comment)
    algolia_index_post_save(post)


@comment_nodes_only
def activity_after_creating_node(comment):
    comment_id = comment['_id']
    parent_id = comment.get('parent', None)

    if not parent_id:
        log.warning('Comment %s created without parent.' % comment_id)
        return

    db = flask.current_app.db()
    parent = db['nodes'].find_one({'_id': parent_id},
                                  projection={'node_type': 1})
    if not parent:
        log.warning('Comment %s has non-existing parent %s' % (comment_id, parent_id))
        return

    log.debug('Recording creation of comment as activity on node %s', parent_id)

    pillar.api.activities.register_activity(
        pillar.api.utils.authentication.current_user_id(),
        'commented',
        'node', comment_id,
        'node', parent_id,
        project_id=comment.get('project', None),
        node_type=comment['node_type'],
    )


def after_creating_comments(nodes):
    for node in nodes:
        activity_after_creating_node(node)
        reindex_post(node)

