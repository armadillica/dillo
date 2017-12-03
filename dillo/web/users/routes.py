import logging

from flask import abort, current_app, render_template

from bson.objectid import ObjectId
from pillarsdk import Node
from pillarsdk import Project
from pillar.web.users.routes import blueprint
from pillar.web import system_util
from pillar.web.utils import attach_project_pictures
from pillar.web.utils import get_file

log = logging.getLogger(__name__)


@blueprint.route('/u/<username>')
def users_view(username):
    """View public user page.

    Use direct db call to retrieve the user and then use the api to query the paginated list of all
    published dillo_posts from the user.

    """
    users_coll = current_app.db('users')
    user = users_coll.find_one(
        {'username': username}, projection={
            'username': 1,
            'full_name': 1,
            'email': 1,
            'extension_props_public': 1,
            '_updated': 1,
            '_created': 1,
        })
    if user is None:
        return abort(404)
    api = system_util.pillar_api()
    nodes_coll = current_app.db('nodes')

    pipeline = [
        {'$match': {'user': ObjectId(user['_id']), 'node_type': 'dillo_post', 'properties.status': 'published'}},
        {'$lookup': {
            'from': 'projects',
            'localField': 'project',
            'foreignField': '_id',
            'as': 'project'}},
        {'$sort': {'_created': -1}},
    ]

    posts = list(nodes_coll.aggregate(pipeline=pipeline))

    for post in posts:
        if post['picture']:
            post['picture'] = get_file(post['picture'], api=api)

    main_project_url = current_app.config['DEFAULT_COMMUNITY']
    project = Project.find_by_url(main_project_url, api=api)
    attach_project_pictures(project, api)

    return render_template(
        'dillo/user.html',
        user=user,
        posts=posts,
        project=project)
