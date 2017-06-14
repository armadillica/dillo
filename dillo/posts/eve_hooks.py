# -*- encoding: utf-8 -*-

"""Hooks for posts types.

On post creation:

- set rating
- calculate hot value
- set shortcode
- set slug from title

"""

import itertools
import logging
import datetime
from bson import ObjectId
from flask import current_app, abort
from micawber.exceptions import ProviderException, ProviderNotFoundException
from slugify import slugify
from pillar.markdown import markdown
from pillar.api.file_storage import generate_link
from pillar.api.nodes import only_for_node_type_decorator
from pillar.api.utils.authentication import current_user_id
from dillo import current_dillo
from dillo.node_types.post import node_type_post
from dillo.utils.sorting import hot
from dillo.shortcodes import generate_shortcode

log = logging.getLogger(__name__)
only_for_post = only_for_node_type_decorator(node_type_post['name'])


def algolia_index_post_save(node):

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': ObjectId(node['project'])})

    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one({'_id': ObjectId(node['user'])})

    rating = node['properties']['rating_positive'] - node['properties']['rating_negative']

    nodes_collection = current_app.data.driver.db['nodes']
    lookup = {'parent': node['_id']}
    comments_count = nodes_collection.count(lookup)

    node_ob = {
        'objectID': node['_id'],
        'name': node['name'],
        'project': {
            '_id': project['_id'],
            'name': project['name']
        },
        'created': node['_created'],
        'updated': node['_updated'],
        'node_type': node['node_type'],
        'user': {
            '_id': user['_id'],
            'full_name': user['full_name']
        },
        'hot': node['properties']['hot'],
        'slug': node['properties']['slug'],
        'category': node['properties']['category'],
        'rating': rating,
        'shortcode': node['properties']['shortcode'],
        'comments_count': comments_count,
    }
    if 'content' in node['properties'] and node['properties']['content']:
        node_ob['content'] = node['properties']['content']
    # Hack for instantsearch.js. Because we can't to string comparison in Hogan, we store this case
    # in a boolean.
    if node['properties']['post_type'] == 'link':
        node_ob['is_link'] = True
    if 'picture' in node and node['picture']:
        files_collection = current_app.data.driver.db['files']
        lookup = {'_id': ObjectId(node['picture'])}
        picture = files_collection.find_one(lookup)

        variation_t = next((item for item in picture['variations']
                            if item['size'] == 't'), None)
        if variation_t:
            node_ob['picture'] = generate_link(picture['backend'],
                                               variation_t['file_path'],
                                               project_id=str(picture['project']),
                                               is_public=True)
    current_app.algolia_index_nodes.save_object(node_ob)


def update_hot(item):
    dt = item['_created']
    dt = dt.replace(tzinfo=datetime.timezone.utc)

    item['properties']['hot'] = hot(
        item['properties']['rating_positive'],
        item['properties']['rating_negative'],
        dt,
    )


@only_for_post
def set_defaults(item):
    # TODO: figure out why properties that have a default value in dyn_schema get it. Once this
    # this happens, we can remove most of the values here and set hot using 0 for default positive
    # and negative ratings.
    item['properties']['content'] = ''
    item['properties']['rating_positive'] = 0
    item['properties']['rating_negative'] = 0
    item['properties']['post_type'] = 'link'
    item['properties']['status'] = 'pending'
    update_hot(item)
    item['properties']['shortcode'] = generate_shortcode(item['project'], item['node_type'])
    item['properties']['slug'] = slugify(item['name'], max_length=50)


def before_creating_posts(items):
    for item in items:
        set_defaults(item)


def convert_to_markdown(item):
    # Convert content from Markdown to HTML.
    try:
        content = item['properties']['content']
    except KeyError:
        item['properties']['content_html'] = ''
    else:
        item['properties']['content_html'] = markdown(content)


def generate_oembed(item):
    # Generate embed code for links.
    try:
        content = item['properties']['content']
    except KeyError:
        # TODO investigate under which circumstances this is allowed
        item['properties']['content_html'] = ''
    else:
        try:
            oembed = current_dillo.oembed_registry.request(content)
            content_html = oembed['html']
        except (ProviderNotFoundException, ProviderException):
            # If the link is not an OEmbed provider, content_html is empty
            content_html = None
        item['properties']['content_html'] = content_html


@only_for_post
def before_replacing_post(item, original):
    if len(item['properties']['content']) < 6:
        log.debug('Content must be longer than 5 chars')
        return abort(422)
    status_original = original['properties']['status']
    status_updated = item['properties']['status']
    if status_original in {'draft', 'pending'} and status_updated in {'pending', 'published'}:
        # We are publishing or editing the post for the first time
        # Update the slug only before the post is published
        item['properties']['slug'] = slugify(item['name'], max_length=50)
    if status_original not in {'draft', 'pending'} and status_updated == 'pending':
        # We do not allow published, pending or deleted posts to be set as pending
        return abort(403)

    post_handler = {
        'link': generate_oembed,
        'text': convert_to_markdown,
    }

    handler = post_handler[item['properties']['post_type']]
    handler(item)
    update_hot(item)
    algolia_index_post_save(item)


@only_for_post
def enrich(response):
    response['_is_own'] = response['user'] == current_user_id()
    response['_current_user_rating'] = None  # tri-state boolean
    response['_rating'] = response['properties']['rating_positive'] - response['properties']['rating_negative']
    if current_user_id():
        if 'ratings' not in response['properties']:
            return
        for rating in response['properties']['ratings'] or ():
            if rating['user'] != current_user_id():
                continue
            response['_current_user_rating'] = rating['is_positive']


def setup_app(app):
    app.on_insert_nodes += before_creating_posts
    app.on_replace_nodes += before_replacing_post
    app.on_fetched_item_nodes += enrich
