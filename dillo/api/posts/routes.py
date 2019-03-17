import logging

from bson import ObjectId
import flask
from flask import abort, Blueprint, current_app, make_response
import pillar
from pillar.api.utils import jsonify

from dillo import EXTENSION_NAME

log = logging.getLogger(__name__)

blueprint_api = Blueprint('posts_api', __name__)


def get_post_additional_properties(community_id: ObjectId):
    """Get post additional properties for a specific community."""
    for k, v in current_app.config['POST_ADDITIONAL_PROPERTIES'].items():
        if community_id not in v['projects']:
            continue
        if 'indexing' not in v or 'faceting' not in v['indexing']:
            continue
        yield k, v


def validate_query_string_page(page):
    """Process the page query string in the request."""
    try:
        page = int(page)
    except ValueError:
        abort(make_response(flask.jsonify({
            '_status': 'ERR',
            'message': 'The argument "page" should be an int.'}), 400))
    except Exception as e:
        logging.error(e)
        abort(make_response(flask.jsonify({
            '_status': 'ERR',
            'message': 'The argument "page" should be an int.'}), 400))
    if page < 1:
        abort(make_response(flask.jsonify({
            '_status': 'ERR',
            'message': 'The argument "page" should be an positive int.'}), 400))
    return page


def validate_query_string_sorting(sorting_key):
    """Process the sorting query string in the request."""
    sorting_options = {
        'new': {'_created': -1},
        'hot': {'properties.hot': -1},
        'top': {'properties.rating_positive': -1}
    }

    # Ensure that sorting key is valid
    if sorting_key not in sorting_options:
        abort(make_response(flask.jsonify({
            '_status': 'ERR',
            'message': 'The argument "sorting" should be "new", "hot" or "top".'}), 400))

    return sorting_options[sorting_key]


def validate_query_string_community(community_id):
    if not community_id:
        return None
    if community_id and not ObjectId.is_valid(community_id):
        abort(make_response(flask.jsonify({
            '_status': 'ERR',
            'message': f'{community_id} is not a valid community id.'}), 400))

    return ObjectId(community_id)


def validate_query_strings(request):
    """Given a request, prepare the query params for get_post().

    Looks for query arguments 'page', 'sorting' and 'filter_tags'.

    Returns:
        A tuple featuring:
        - page: 1
        - sorting: 'hot'
        - filters: dict
        - community_id: ObjectId() or None
    """

    # Handle pagination
    page = validate_query_string_page(request.args.get('page', 1))

    # Handle sorting (new, hot, top) with hardcoded order
    sorting = validate_query_string_sorting(request.args.get('sorting', 'hot'))

    # Handle community_id
    community_id = validate_query_string_community(request.args.get('community_id'))

    # Handle title search
    title = request.args.get('title')

    # Handle filters
    filters = {}

    filter_tags = request.args.getlist('filter_tags[]')
    if filter_tags:
        filters['tags'] = filter_tags

    # This involves looking up community-specific filters
    if community_id:
        for k, v in get_post_additional_properties(community_id):
            additional_filter = request.args.getlist(f'filter_{k}[]')
            if additional_filter:
                filters[k] = additional_filter

    return page, sorting, filters, community_id, title


def add_communities_filter(pipeline):
    """Given an aggregation pipeline, add a filter for communities."""

    current_user = pillar.auth.get_current_user()

    default_followed_community_ids = current_app.config['DEFAULT_FOLLOWED_COMMUNITY_IDS']
    # Add filter for communities
    if current_user.is_anonymous and default_followed_community_ids:
        pipeline[0]['$match']['project'] = {'$in': default_followed_community_ids}
    elif current_user.is_authenticated:
        users_coll = current_app.db('users')
        followed_communities_key = f'extension_props_public.{EXTENSION_NAME}.followed_communities'
        # TODO(fsiddi) project into a shorter key instead of followed_communities
        followed = users_coll.find_one({
            '_id': current_user.user_id,
            followed_communities_key: {'$exists': True}
        }, {followed_communities_key: 1})
        # If current user is following communities, use them as filter
        if followed:
            fcl = followed['extension_props_public'][EXTENSION_NAME]['followed_communities']
            communities = [c for c in fcl]
            pipeline[0]['$match']['project'] = {'$in': communities}
        # Otherwise, try to use default communities
        elif default_followed_community_ids:
            pipeline[0]['$match']['project'] = {'$in': default_followed_community_ids}


def add_facets_to_pipeline(pipeline, community_id):
    """Given an aggregation pipeline, add elements to the facet step."""
    pipeline[2]['$facet']['facet_tags'] = [
        {'$unwind': '$properties.tags'},
        {'$sortByCount': '$properties.tags'}
      ]

    # If no community id is specified, do not look for custom facets
    if not community_id:
        return

    for k, v in get_post_additional_properties(community_id):
        pipeline[2]['$facet'][f'facet_{k}'] = [
            {'$unwind': f'$properties.{k}'},
            {'$sortByCount': f'$properties.{k}'}
        ]


def add_facets_to_response(doc, posts_cursor, community_id):
    """Move all facets in a 'facet' property."""
    doc['facets'] = {'tags': {
        'items': posts_cursor['facet_tags'],  # The actual facet options
        'label': 'Tags',  # A human-readable label
        'filter': 'filter_tags[]',  # The query string to use when performing requests
    }}
    if not community_id:
        return
    for k, v in get_post_additional_properties(community_id):
        doc['facets'][k] = {
            'items': posts_cursor[f'facet_{k}'],
            'label': v['label'],  # A human-readable label
            'filter': f'filter_{k}[]',  # The query string to use when performing requests
        }


def add_filter_tags(pipeline, filter_tags):
    pipeline[0]['$match']['properties.tags'] = {'$in': filter_tags}


def add_filter_community(pipeline, filter_community):
    pipeline[0]['$match']['project'] = ObjectId(filter_community)


@blueprint_api.route('/')
def get_posts():
    """Fetch list of paginated posts.

    If the user is logged in, show posts based on the followed communities.
    Supported query parameters:

    - page
    - sorting (hot, top, new)
    - filters (tags, development_status)

    We limit the amount of results to 15 (config PAGINATION_DEFAULT_POSTS) per request.
    Together with data and metadata, we also return 'facets' which act as 'filters'
    when performing requests to this endpoint.
    """

    # Validate query parameters and define sorting and pagination
    page, sorting, filters, community_id, title = validate_query_strings(flask.request)
    pagination_default = current_app.config['PAGINATION_DEFAULT_POSTS']
    skip = pagination_default * (page - 1)

    pipeline = [
        # Find all Dillo posts that are published and not deleted
        # Optionally, require posts from communities that the user follows
        # or from the DEFAULT_FOLLOWED_COMMUNITY_IDS list
        {'$match': {
            'node_type': 'dillo_post',
            'properties.status': 'published',
            '_deleted': {'$ne': True}}},
        # Sort them by most recent (or by hot)
        {'$sort': sorting},
        # Create facets
        # Store total document count in metadata
        # Further process the posts in data
        {'$facet': {
            'metadata': [{'$count': 'total'}, {'$addFields': {'page': page}}],
            'data': [
                {'$skip': skip},
                {'$limit': pagination_default},
                # Aggregate the project
                {'$lookup': {
                    'from': 'projects',
                    'localField': 'project',
                    'foreignField': '_id',
                    'as': 'project'}},
                {'$unwind': '$project'},
                # Aggregate the user
                {'$lookup': {
                    'from': 'users',
                    'localField': 'user',
                    'foreignField': '_id',
                    'as': 'user'}},
                {'$unwind': '$user'},
                {'$project': {
                    'name': 1,
                    'properties': 1,
                    'picture': 1,
                    '_created': 1,
                    'project.url': 1,
                    'project.name': 1,
                    'user': '$user.username'
                }},
            ]
        }},
    ]

    if community_id:
        # If a community is specified, show only posts that belong to it
        add_filter_community(pipeline, community_id)
    else:
        # We are not viewing a community, use the aggregated communities
        add_communities_filter(pipeline)

    for filter_key, filter_value in filters.items():
        pipeline[0]['$match'][f'properties.{filter_key}'] = {'$in': filter_value}

    if title:
        pipeline[0]['$match']['$text'] = {'$search': title}

    # Add default facets, as well as community-specific facets
    add_facets_to_pipeline(pipeline, community_id)

    nodes_coll = current_app.db('nodes')
    # The cursor will return only one item in the list
    posts_cursor = list(nodes_coll.aggregate(pipeline=pipeline))[0]

    # Set default values for metadata (in case no result was retrieved)
    metadata = {'total': 0, 'page': 1}
    if posts_cursor['metadata']:
        metadata = posts_cursor['metadata'][0]  # Only the first element from the list

    docs = {
        'metadata': metadata,
        'data': posts_cursor['data'],
        'filters': filters,
    }

    add_facets_to_response(docs, posts_cursor, community_id)

    return jsonify(docs)


def update_download_count(post_id):
    """Update download count for the Post.

    This function is called from dillo.web.posts.routes.download_file.
    """

    current_app.db('nodes').update_one(
        {'_id': ObjectId(post_id)},
        {'$inc': {'properties.downloads_total': 1, 'properties.downloads_latest': 1}})

    log.debug('Updated download count for post %s' % post_id)
    return jsonify({'status': 'OK'})
