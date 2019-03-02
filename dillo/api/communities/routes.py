import logging
from bson import ObjectId

from flask import Blueprint, current_app, abort, jsonify

from pillar.api.utils.authorization import require_login
from pillar.api.utils import str2id
from pillar.auth import current_user

from dillo import EXTENSION_NAME


log = logging.getLogger(__name__)
blueprint_api = Blueprint('communities_api', __name__)


def get_community(project_id: str):
    """Fetch a valid community by its string id."""

    # Cast to ObjectId
    project_id = str2id(project_id)

    # Ensure the project exists
    projects_coll = current_app.db('projects')
    community = projects_coll.find_one({
        '_id': project_id,
        '_deleted': {'$ne': True},
    },
        {f'extension_props.{EXTENSION_NAME}': 1, 'name': 1}
    )
    if not community:
        log.debug('Project %s does not exist' % project_id)
        return abort(404)

    # Ensure the project is a community (was setup_for_dillo)
    if EXTENSION_NAME not in community['extension_props']:
        log.warning('Project %s is not a setup for Dillo and can not be followed' % project_id)
        return abort(403)

    return community


@blueprint_api.route('/follow/<string(length=24):project_id>', methods=['POST'])
@require_login()
def follow(project_id: str):
    """Add the community to followed_communities."""
    # Ensure that the community requested exists
    community = get_community(project_id)

    users_coll = current_app.db('users')

    # Fetch user
    user = users_coll.find_one(current_user.user_id)
    # Look for project in in extension_props_public.dillo.followed_communities
    followed_communities = user['extension_props_public'][EXTENSION_NAME].\
        get('followed_communities')

    # Check if the user already follows the community
    if followed_communities and community['_id'] in followed_communities:
        log.debug('User already follows community %s' % community['url'])
        return abort(403)

    followed_communities_key = f'extension_props_public.{EXTENSION_NAME}.followed_communities'
    users_coll.update_one(
        {'_id': current_user.user_id},
        {'$addToSet': {followed_communities_key: community['_id']}})

    return jsonify({'_status': 'OK',
                    'message': f"Following {community['name']}"})


@blueprint_api.route('/unfollow/<string(length=24):project_id>', methods=['POST'])
@require_login()
def unfollow(project_id: str):
    """Remove a community from followed_communities of current_user."""
    # Ensure that the community requested exists
    community = get_community(project_id)

    users_coll = current_app.db('users')

    # Fetch user
    user = users_coll.find_one(current_user.user_id)
    # Look for project in in extension_props_public.dillo.followed_communities
    followed_communities = user['extension_props_public'][EXTENSION_NAME]. \
        get('followed_communities')

    if not followed_communities:
        log.debug('User does not follow any community.')
        return abort(400)

    # Check if the user already does not follow the community
    if followed_communities and community['_id'] not in followed_communities:
        log.debug('User does not follow community %s' % community['url'])
        return abort(403)

    followed_communities_key = f'extension_props_public.{EXTENSION_NAME}.followed_communities'
    users_coll.update_one(
        {'_id': current_user.user_id},
        {'$pull': {followed_communities_key: community['_id']}})

    log.debug('Community %s successfully unfollowed' % community['name'])
    return jsonify({'_status': 'OK',
                    'message': f"Unfollowed {community['name']}"})
