import logging

from flask import Blueprint, current_app, redirect, render_template, url_for
from werkzeug import exceptions as wz_exceptions
from flask_login import current_user

from pillarsdk import Project
from pillarsdk import Activity
from pillarsdk.nodes import Node

from pillar.web import subquery
from pillar.web import system_util

blueprint = Blueprint('posts', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/post')
def create():

    api = system_util.pillar_api()
    log.info('Creating post for user {}'.format(current_user.objectid))
    project = current_app.config['MAIN_PROJECT_ID']

    post_props = dict(
        project=project,
        name='My Post',
        user=current_user.objectid,
        node_type='dillo_post',
        properties=dict(
            category='community',)
    )

    post = Node(post_props)
    post.create(api=api)

    return redirect(url_for('nodes.edit', node_id=post._id))


@blueprint.route('/p/')
def index():
    api = system_util.pillar_api()

    # Fetch all activities for the main project
    activities = Activity.all({
        'where': {
            'project': current_app.config['MAIN_PROJECT_ID'],
        },
        'sort': [('_created', -1)],
        'max_results': 20,
    }, api=api)

    # Fetch more info for each activity.
    for act in activities['_items']:
        act.actor_user = subquery.get_user_info(act.actor_user)

    return render_template(
            'dillo/search.html',
            activities=activities)
