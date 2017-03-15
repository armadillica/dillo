import logging

from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug import exceptions as wz_exceptions
from flask_login import current_user
from pillarsdk.nodes import Node
from pillar.web import system_util

from dillo import current_dillo

blueprint = Blueprint('dillo', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    api = system_util.pillar_api()
    from flask import redirect, url_for
    #return redirect(url_for('index'))
    return render_template('dillo/index.pug')


@blueprint.route('/post')
def post_create():

    api = system_util.pillar_api()
    log.info('Creating post for user {}'.format(current_user.objectid))
    project = current_app.config['MAIN_PROJECT_ID']

    comment_props = dict(
        project=project,
        name=' ',
        user=current_user.objectid,
        node_type='dillo_post',
        properties=dict(
            category='community',
            status='pending',
            rating_positive=0,
            rating_negative=0))

    comment = Node(comment_props)
    comment.create(api=api)

    return jsonify({'node_id': comment._id}), 201
