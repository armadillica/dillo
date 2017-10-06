import logging

from algoliasearch.helpers import AlgoliaException
import bson

from pillar import current_app


log = logging.getLogger(__name__)


@current_app.celery.task(ignore_result=True)
def algolia_index_user_posts(user_id: str):
    """Reindex all published posts for a certain user."""

    from dillo.api.posts.hooks import algolia_index_post_save

    user_oid = bson.ObjectId(user_id)
    log.info('Retrieving posts for user %s', user_oid)

    nodes_coll = current_app.db('nodes')
    posts = nodes_coll.find({
        'user': user_oid,
        'node_type': 'dillo_post',
        'properties.status': 'published'})
    for post in posts:
        try:
            algolia_index_post_save(post)
        except AlgoliaException as ex:
            log.warning('Unable to push node info to Algolia for node %s; %s', post['_id'], ex)
