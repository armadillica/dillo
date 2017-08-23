import logging
import requests
from urllib.parse import urlparse, urljoin
from re import compile

from bs4 import BeautifulSoup
from micawber.exceptions import ProviderException, ProviderNotFoundException
from flask import abort, Blueprint, current_app, redirect, render_template, request, url_for, \
    jsonify
from werkzeug import exceptions as wz_exceptions
from werkzeug.contrib.atom import AtomFeed
from flask_login import current_user, login_required
from pillarsdk import Project
from pillarsdk import Activity
from pillarsdk.nodes import Node

from pillar.web import subquery
from pillar.web import system_util

from dillo import current_dillo

blueprint = Blueprint('posts', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/post/<post_type>')
def create(post_type: str):
    api = system_util.pillar_api()
    log.info('Creating post for user {}'.format(current_user.objectid))

    post_props = dict(
        project=current_app.config['MAIN_PROJECT_ID'],
        name='My Post',
        user=current_user.objectid,
        node_type='dillo_post',
        properties=dict(
            category=current_app.config['POST_CATEGORIES'][0],
            post_type=post_type)
    )

    post = Node(post_props)
    post.create(api=api)
    embed = request.args.get('embed')
    return redirect(url_for('nodes.edit', node_id=post._id, embed=embed))


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
            'dillo/index.html',
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
        'dillo/index.html',
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

    o = urlparse(r.url)
    url_no_query = o.scheme + "://" + o.netloc + o.path

    soup = BeautifulSoup(r.content, 'html5lib')

    # Get the page title
    if soup.title:
        parsed_page['title'] = soup.title.string

    # Get the favicon
    icon_link = soup.find('link', rel='icon')
    if icon_link:
        icon_link_href = icon_link['href']
        # If the URL is relative
        if not urlparse(icon_link_href).netloc:
            icon_link_href = urljoin(url_no_query, icon_link_href)
        parsed_page['favicon'] = icon_link_href

    parsed_page['images'] = []

    # Look for oembed
    try:
        oembed = current_dillo.oembed_registry.request(r.url)
        parsed_page['oembed'] = oembed['html']
        if 'thumbnail_url' in oembed:
            validate_append_image(oembed['thumbnail_url'], url_no_query, parsed_page['images'])
            log.debug('Appending image %s and returning' % oembed['thumbnail_url'])
            return jsonify(parsed_page)
    except (ProviderNotFoundException, ProviderException):
        log.debug('No Oembed thumbnail found')

    # Get meta Open Graph
    images_og = soup.find_all('meta', attrs={'property': 'og:image'})
    for image_og in images_og:
        validate_append_image(image_og['content'], url_no_query, parsed_page['images'])

    # Get meta Twitter, only if Open Graph is not available
    image_tw = soup.find('meta', attrs={'name': 'twitter:image'})
    if image_tw and not images_og:
        validate_append_image(image_tw['content'], url_no_query, parsed_page['images'])

    # Get all images
    images = soup.find_all('img', attrs={'src': compile('.')})
    log.debug('Found %i images' % len(images))
    for image in images:
        validate_append_image(image['src'], url_no_query, parsed_page['images'])

    # Last resort, check if the link itself is an image
    if len(parsed_page['images']) == 0:
        validate_append_image(r.url, None, parsed_page['images'])

    return jsonify(parsed_page)


def validate_append_image(image_url, base_url, images_list):
    """Given an image URL, check its suitability for thumbnailing"""
    if len(images_list) > 3:
        return

    if not image_url.startswith('http'):
        # Strip url from extensions
        image_url = base_url + image_url

    image_head = requests.head(image_url)

    # Check if header is available
    try:
        content_length = int(image_head.headers['content-length'])
        content_type = image_head.headers['content-type']
        if content_length > 1024 and content_type.startswith('image'):
            # If the image is larger than 1KB
            log.debug('Appending image %s' % image_url)
            images_list.append(image_url)
        else:
            log.debug('Skipping small image %s' % image_url)
    except KeyError:
        log.debug('Skipping image %s because of missing content-length header' % image_url)


@blueprint.route('/p/feed/latest.atom')
def feeds_blogs():
    """Global feed generator for latest blogposts across all projects"""
    # @current_app.cache.cached(60*5)
    def render_page():
        feed = AtomFeed('Dillo - Latest updates',
                        feed_url=request.url,
                        url=request.url_root)
        # Get latest posts
        api = system_util.pillar_api()
        latest_posts = Node.all({
            'where': {'node_type': 'dillo_post', 'properties.status': 'published'},
            'embedded': {'user': 1},
            'sort': '-_created',
            'max_results': '15'
            }, api=api)

        # Populate the feed
        for post in latest_posts._items:
            author = post.user.full_name
            updated = post._updated if post._updated else post._created
            url = url_for('posts.view', post_shortcode=post.properties.shortcode)
            content = post.properties.content[:500]
            feed.add(post.name, str(content),
                     content_type='html',
                     author=author,
                     url=url,
                     updated=updated,
                     published=post._created)
        return feed.get_response()
    return render_page()
