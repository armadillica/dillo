import logging

import requests
from re import compile
from bs4 import BeautifulSoup
from micawber.exceptions import ProviderException, ProviderNotFoundException
from flask import abort, Blueprint, current_app, redirect, render_template, request, url_for, \
    jsonify
from werkzeug import exceptions as wz_exceptions
from flask_login import current_user, login_required
from pillarsdk import Project
from pillarsdk import Activity
from pillarsdk.nodes import Node

from pillar.web import subquery
from pillar.web import system_util

from dillo import current_dillo

blueprint = Blueprint('posts', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/post')
def create():
    api = system_util.pillar_api()
    log.info('Creating post for user {}'.format(current_user.objectid))

    post_props = dict(
        project=current_app.config['MAIN_PROJECT_ID'],
        name='My Post',
        user=current_user.objectid,
        node_type='dillo_post',
        properties=dict(
            category=current_app.config['POST_CATEGORIES'][0])
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
            col_right={'activities': activities})


@blueprint.route("/p/<string(length=24):post_id>/rate/<operation>", methods=['POST'])
@login_required
def post_rate(post_id, operation):
    """Comment rating function

    :param post_id: the post aid
    :type post_id: str
    :param operation: the rating 'revoke', 'upvote', 'downvote'
    :type operation: string

    """

    if operation not in {'revoke', 'upvote', 'downvote'}:
        raise wz_exceptions.BadRequest('Invalid operation')

    api = system_util.pillar_api()

    # PATCH the node and return the result.
    comment = Node({'_id': post_id})
    result = comment.patch({'op': operation}, api=api)
    assert result['_status'] == 'OK'

    return jsonify({
        'status': 'success',
        'data': {
            'op': operation,
            'rating_positive': result.properties.rating_positive,
            'rating_negative': result.properties.rating_negative,
        }})


@blueprint.route('/p/<string(length=6):post_shortcode>/')
@blueprint.route('/p/<string(length=6):post_shortcode>/<slug>')
def view(post_shortcode, slug=None):
    api = system_util.pillar_api()
    post = Node.find_one({'where': {'properties.shortcode': post_shortcode}}, api=api)
    return render_template(
        'dillo/search.html',
        col_right={'post': post})


@blueprint.route('/spoon', methods=['POST'])
def spoon():
    """Parse a url and return:
    - title: the page title
    - images: an array of max 4 images found on the page
    - oembed: html code for oembed (if available)
    """

    url = request.form.get('url')

    if not url:
        return abort(400)

    parsed_page = {
        'images': [],
        'title': '',
        'favicon': None,
        'oembed': None,
    }

    try:
        r = requests.get(url)
    except requests.exceptions.MissingSchema as e:
        log.debug(e)
        return abort(422)

    if not r.ok:
        log.debug('Bad return code: %s', r.status_code)
        return abort(422)

    soup = BeautifulSoup(r.content, 'html5lib')

    # Get the page title
    if soup.title:
        parsed_page['title'] = soup.title.string

    # Get the favicon
    icon_link = soup.find('link', rel='shortcut icon')
    if icon_link:
        parsed_page['favicon'] = icon_link['href']

    # Get only the first 4 images (with an src tag)
    images = soup.find_all('img', attrs={'src': compile('.')})
    parsed_page['images'] = [i['src'] for i in images[:4]]

    # Look for oembed
    try:
        oembed = current_dillo.oembed_registry.request(r.url)
        parsed_page['oembed'] = oembed['html']
        if 'thumbnail_url' in oembed:
            parsed_page['images'] = [oembed['thumbnail_url']]
    except (ProviderNotFoundException, ProviderException):
        pass

    return jsonify(parsed_page)
