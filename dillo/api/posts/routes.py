import logging
import json

from bson import ObjectId
from flask import Blueprint, current_app, jsonify

import pillar
from pillar.api.utils import PillarJSONEncoder

log = logging.getLogger(__name__)

blueprint_api = Blueprint('posts_api', __name__)


@blueprint_api.route('/')
def get_posts():
    """Fetch list of paginated posts.

    If the user is logged in, show posts based on the followed communities.
    """

    pipeline = [
        # Find all Dillo posts that are published and not deleted
        # Optionally, require posts from communities that the user follows
        # or from the DEFAULT_FOLLOWED_COMMUNITY_IDS list
        {'$match': {
            'node_type': 'dillo_post',
            'properties.status': 'published',
            '_deleted': {'$ne': True}}},
        # Sort them by most recent (or by hot)
        {'$sort': {'_created': -1}},
        # Create facets
        # Store total document count in metadata
        # Further process the posts in data
        {'$facet': {
            'metadata': [{'$count': "total"}, {'$addFields': {'page': 1}}],
            'data': [
                {'$skip': 0},
                {'$limit': 10},
                {'$lookup': {
                    'from': 'projects',
                    'localField': 'project',
                    'foreignField': '_id',
                    'as': 'project'}},
                {'$project': {
                    'name': 1,
                    'properties': 1,
                    'user': 1,
                    'picture': 1,
                    '_created': 1,
                    'project': {'$arrayElemAt': ['$project', 0]}
                }},
            ]
        }},

    ]

    current_user = pillar.auth.get_current_user()

    # Replace community id string with ObjectId
    default_followed_community_ids = [ObjectId(cid) for cid in
                                      current_app.config['DEFAULT_FOLLOWED_COMMUNITY_IDS']]

    # Add filter for communities
    if current_user.is_anonymous and default_followed_community_ids:
        pipeline[0]['$match']['project'] = {'$in': default_followed_community_ids}
    elif current_user.is_authenticated:
        pass
        # If current user is following communities filter them
        # Else, try to use default communities

    nodes_coll = current_app.db('nodes')
    # The cursor will return only one item in the list
    posts_cursor = list(nodes_coll.aggregate(pipeline=pipeline))

    js = PillarJSONEncoder()
    en = json.loads(js.encode(posts_cursor[0]['data']))
    return jsonify({
        'metadata': posts_cursor[0]['metadata'],
        'data': en,
    })
