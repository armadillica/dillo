import logging

from flask import Blueprint, redirect, url_for, jsonify
from flask_login import login_required, current_user
from bson import ObjectId


from pillar import current_app

blueprint = Blueprint('dillo', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    return redirect(url_for('posts.index'))


@login_required
@blueprint.route('/ratings')
def get_user_ratings():
    """Aggregation pipeline for all posts rated by current user. Should be cached?
    """

    def get_ratings(user_id: ObjectId) -> list:
        pipeline = [
            {
                '$match': {
                    '_deleted': {'$ne': True},
                    'properties.ratings': {'$exists': True}
                }
            },
            {
                '$project': {
                    'properties.ratings': 1
                }
            },
            {
                '$unwind': {
                    'path': '$properties.ratings',
                }
            },
            {
                '$match': {
                    'properties.ratings.user': user_id
                }
            },
        ]
        c = current_app.db()['nodes']
        # Return either a list with one item or an empty list
        r = list(c.aggregate(pipeline=pipeline))
        return r

    ratings = get_ratings(ObjectId(current_user.objectid))
    trim_ratings = dict((str(r['_id']), r['properties']['ratings']['is_positive']) for r in ratings)

    return jsonify(items=trim_ratings)
