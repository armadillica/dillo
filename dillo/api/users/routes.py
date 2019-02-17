import logging

from flask import current_app, abort, jsonify

from pillar.api.utils.authorization import require_login
from pillar.api.users.routes import blueprint_api
from pillar.api.utils import str2id
from pillar.auth import current_user

from dillo import EXTENSION_NAME

log = logging.getLogger(__name__)


@blueprint_api.route('/follow/<string(length=24):project_id>', methods=['POST'])
@require_login()
def follow_community(project_id: str):
    """Add the community to followed_communities."""

    project_id = str2id(project_id)

    # TODO(fsiddi) Check if the user already follows the community
    # Fetch user
    # Look for project in in extension_props_public.dillo.followed_communities

    # Ensure the project exists
    projects_coll = current_app.db('projects')
    community = projects_coll.find_one({
        '_id': project_id,
        '_deleted': {'$ne': True},
    },
        {f'extension_props.{EXTENSION_NAME}': 1}
    )
    if not community:
        log.debug('Project %s does not exist' % project_id)
        return abort(404)

    # Ensure the project is a community (was setup_for_dillo)
    if EXTENSION_NAME not in community['extension_props']:
        log.warning('Project %s is not a setup for Dillo and can not be followed' % project_id)
        return abort(403)

    users_coll = current_app.db('users')
    followed_communities_key = f'extension_props_public.{EXTENSION_NAME}.followed_communities'
    users_coll.update_one(
        {'_id': current_user.user_id},
        {'$addToSet': {followed_communities_key: project_id}})

    return jsonify({'_status': 'OK'})

