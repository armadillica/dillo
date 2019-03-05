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
from flask_babel import gettext as _
from pillarsdk import Project, Node, Activity, User
from pillarsdk.exceptions import ResourceNotFound, ForbiddenAccess

from pillar.web import subquery
from pillar.web import system_util
from pillar.web.utils import attach_project_pictures
from pillar.web.utils import get_file
from pillar.web.utils import get_main_project
from pillar.web.nodes.routes import url_for_node

from dillo import current_dillo
from dillo.web.posts.utils import project_submit_menu

blueprint = Blueprint('posts', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/nodes/<string(length=24):node_id>/view')
def view_embed(node_id):
    api = system_util.pillar_api()

    # Get node, we'll embed linked objects later.
    try:
        node = Node.find(node_id, api=api)
    except ResourceNotFound:
        return render_template('errors/404_embed.html')
    except ForbiddenAccess:
        return render_template('errors/403_embed.html')

    project_projection = {'project': {'url': 1, 'name': 1}}
    project = Project.find(node.project, project_projection, api=api)

    node.picture = get_file(node.picture, api=api)
    node.user = node.user and User.find(node.user, api=api)

    write_access = 'PUT' in (node.allowed_methods or set())

    extra_template_args = {'project': project}

    return render_template(
        'nodes/custom/dillo_post/view_embed.html',
        node_id=node._id,
        node=node,
        write_access=write_access,
        api=api,
        **extra_template_args)


@blueprint.route('/c/<community_url>/post/<post_type>')
def create(community_url: str, post_type: str):
    api = system_util.pillar_api()

    project = Project.find_first({'where': {'url': community_url}}, api=api)
    if project is None:
        return abort(404)

    log.info('Creating post for user {}'.format(current_user.objectid))

    dillo_post_node_type = project.get_node_type('dillo_post')
    dillo_post_tags_default = dillo_post_node_type['dyn_schema']['tags']['schema']['default']

    post_props = dict(
        project=project['_id'],
        name='Awesome Post Title',
        user=current_user.objectid,
        node_type='dillo_post',
        properties=dict(
            tags=[dillo_post_tags_default, ],
            post_type=post_type)
    )

    post = Node(post_props)
    post.create(api=api)
    embed = request.args.get('embed')
    return redirect(url_for(
        'nodes.edit', node_id=post._id, embed=embed, _external=True,
        _scheme=current_app.config['SCHEME']))


@blueprint.route('/posts/')
def posts_list():
    """Generate an embeddable list of posts.

    Aggregated view of all posts for the public communities.

    If a user has a set of favourite communites in its settings, use those
    instead.
    """
    api = system_util.pillar_api()

    # Build base url for API request
    url = '/api/posts/?'

    # Iterate over query strings
    for qs, qv in request.args.items():
        # Append to API url only query string with a value
        if qv:
            url += f'{qs}={qv}&'

    posts_request = api.http_call(url, method='GET')
    posts = posts_request['data']
    # Attach pictures
    for post in posts:
        if post.get('picture'):
            post['picture'] = get_file(post['picture'], api=api)

    # Check if we are at the last page
    is_last_page = False
    if len(posts) < current_app.config['PAGINATION_DEFAULT_POSTS']:
        is_last_page = True

    return render_template(
        'dillo/posts_list.html',
        posts=posts,
        metadata=posts_request['metadata'],
        facets=posts_request['facets'],
        is_last_page=is_last_page,
    )


@blueprint.route('/c/')
def index_all():
    """Landing page. Posts are loaded asynchronously."""
    api = system_util.pillar_api()
    project = get_main_project()
    attach_project_pictures(project, api)

    return render_template(
        'dillo/index_followed.html',
        col_right={'activities': {'_meta': {'total': 0}}},
        project=project)


def is_community_followed(community) -> bool:
    """Check if the community is followed."""

    if current_user.is_anonymous:
        return False

    # Community is not followed by default
    community_is_followed = False

    # Define the communities followed by default
    followed_communities = [cid for cid in
                            current_app.config['DEFAULT_FOLLOWED_COMMUNITY_IDS']]

    user = User.find(current_user.objectid, api=system_util.pillar_api())
    # If 'followed_communities' for the user exists and is not an empty list
    if 'followed_communities' in user['extension_props_public']['dillo'] \
            and user['extension_props_public']['dillo']['followed_communities']:
        followed_communities = user['extension_props_public']['dillo']['followed_communities']

    if community['_id'] in followed_communities:
        community_is_followed = True

    return community_is_followed


@blueprint.route('/c/<community_url>/')
def index(community_url):
    api = system_util.pillar_api()

    project = Project.find_first({'where': {'url': community_url}}, api=api)

    if project is None:
        return abort(404)

    attach_project_pictures(project, api)

    community_is_followed = is_community_followed(project)

    # Fetch all activities for the project
    activities = Activity.all({
        'where': {
            'project': project['_id'],
        },
        'sort': [('_created', -1)],
        'max_results': 15,
    }, api=api)

    # Fetch more info for each activity.
    for act in activities['_items']:
        act.actor_user = subquery.get_user_info(act.actor_user)
        try:
            act.link = url_for_node(node_id=act.object)
        except ValueError:
            # If the node was delete, we get ValueError exception.
            # By setting act.link to '', it does not get displayed in the list.
            act.link = ''

    return render_template(
        'dillo/index_followed.html',
        col_right={'activities': activities},
        project=project,
        submit_menu=project_submit_menu(project),
        community_is_followed=community_is_followed,)


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


@blueprint.route('/c/<community_url>/<string(length=6):post_shortcode>/')
@blueprint.route('/c/<community_url>/<string(length=6):post_shortcode>/<slug>')
def view(community_url, post_shortcode, slug=None):
    api = system_util.pillar_api()
    project = Project.find_by_url(community_url, api=api)
    attach_project_pictures(project, api)

    post = Node.find_one({
        'where': {
            'project': project['_id'],
            'properties.shortcode': post_shortcode},
        'embedded': {'user': 1}}, api=api)

    if post.picture:
        post.picture = get_file(post.picture, api=api)

    return render_template(
        'dillo/index.html',
        project=project,
        submit_menu=project_submit_menu(project),
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


def populate_feed(feed: AtomFeed, latest_posts):
    """Populate the feed with the provided data."""
    for post in latest_posts._items:
        api = system_util.pillar_api()
        author = post.user.full_name
        updated = post._updated if post._updated else post._created
        project_projection = {'project': {'url': 1}}
        project = Project.find(post.project, project_projection, api=api)
        url = url_for('posts.view', post_shortcode=post.properties.shortcode,
                      community_url=project.url)
        content = post.properties.content[:500]
        feed.add(post.name, str(content),
                 content_type='html',
                 author=author,
                 url=url,
                 updated=updated,
                 published=post._created)


@blueprint.route('/c/feed/latest.atom')
def feed_all_communities():
    """Global feed generator for latest posts across all projects."""
    # @current_app.cache.cached(60*5)
    def render_page():
        project = get_main_project()
        feed = AtomFeed(f'{project.name} - Latest updates',
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

        populate_feed(feed, latest_posts)
        return feed.get_response()
    return render_page()


@blueprint.route('/c/<community_url>/feed/latest.atom')
def feed_community(community_url):
    """Project feed generator for latest blogposts across a single Project."""
    # @current_app.cache.cached(60*5)
    def render_page():
        # Get latest posts
        api = system_util.pillar_api()
        project = Project.find_first({'where': {'url': community_url}}, api=api)
        if not project:
            abort(404)

        feed = AtomFeed(project.name + ' - ' + _('Latest updates'),
                        feed_url=request.url,
                        url=request.url_root)

        latest_posts = Node.all({
            'where': {'node_type': 'dillo_post', 'properties.status': 'published',
                      'project': project['_id']},
            'embedded': {'user': 1},
            'sort': '-_created',
            'max_results': '15'
            }, api=api)

        populate_feed(feed, latest_posts)
        return feed.get_response()
    return render_page()
