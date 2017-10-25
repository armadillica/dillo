# -*- encoding: utf-8 -*-

"""Hooks for posts types.

On post creation:

- set rating
- calculate hot value
- set shortcode
- set slug from title

"""

import datetime
import imghdr
import logging
import mimetypes
import requests
import tempfile
import os.path
from urllib.parse import urlparse
from bson import ObjectId
from werkzeug.datastructures import FileStorage
from flask import current_app, abort
from micawber.exceptions import ProviderException, ProviderNotFoundException
from slugify import slugify
from pillar.markdown import markdown
from pillar.api.file_storage import generate_link
from pillar.api.nodes import only_for_node_type_decorator
from pillar.api.utils.authentication import current_user_id
from pillar.api.file_storage import upload_and_process
from pillar.api.activities import activity_subscribe
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
            'name': project['name'],
            'url': project['url'],
        },
        'created': node['_created'],
        'updated': node['_updated'],
        'node_type': node['node_type'],
        'user': {
            '_id': user['_id'],
            'full_name': user['full_name'],
            'username': user['username'],
        },
        'hot': node['properties']['hot'],
        'slug': node['properties']['slug'],
        'tags': node['properties']['tags'],
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

        variation_s = next((item for item in picture['variations']
                            if item['size'] == 's'), None)
        if variation_s:
            node_ob['picture'] = generate_link(picture['backend'],
                                               variation_s['file_path'],
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
    item['properties']['rating_positive'] = 1
    item['properties']['rating_negative'] = 0
    item['properties']['status'] = 'pending'
    update_hot(item)
    item['properties']['shortcode'] = generate_shortcode(item['project'], item['node_type'])
    item['properties']['slug'] = slugify(item['name'], max_length=50)
    # Give the current user PUT access. Only he will be able to update the post.
    item['permissions'] = {'users': [{'user': current_user_id(), 'methods': ['PUT']}]}


def before_inserting_posts(items):
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
    if status_updated == 'draft':
        if status_original in {'pending', 'draft'}:
            pass
        else:
            return abort(422)
    elif status_updated == 'published':
        if status_original in {'pending', 'draft'}:
            # We are publishing or editing the post for the first time
            # Update the slug only before the post is published
            item['properties']['slug'] = slugify(item['name'], max_length=50)
        elif status_original == 'published':
            pass
        else:
            return abort(422)
    else:
        # Combination of status_updated and status_original is not allowed
        return abort(422)

    post_handler = {
        'link': generate_oembed,
        'text': convert_to_markdown,
    }

    handler = post_handler[item['properties']['post_type']]
    handler(item)
    update_hot(item)
    algolia_index_post_save(item)


@only_for_post
def process_picture_oembed(item, original):
    """If picture_oembed is specified, download the image and populate the picture property."""
    picture_url = item['properties']['picture_url']
    if picture_url:
        # Download file to temp location
        r = requests.get(picture_url, stream=True)
        # Throw an error for bad status codes
        r.raise_for_status()
        with tempfile.NamedTemporaryFile() as f:
            for block in r.iter_content(1024):
                f.write(block)
            # Parse url to get the filename
            picture_url_parsed = urlparse(picture_url)
            filename = os.path.basename(picture_url_parsed.path)
            mimetype, _ = mimetypes.guess_type(filename, strict=False)
            # TODO use python-magic to determine mime type (directly in upload_and_process)
            if not mimetype:
                image_type = imghdr.what(f)
                mimetype = f'image/{image_type}'
            fs = FileStorage(stream=f, filename=filename, content_type=mimetype)
            result = upload_and_process(f, fs, str(item['project']))
            # Update item before saving
            if result['status'] == 'ok':
                item['picture'] = ObjectId(result['file_id'])
        item['properties']['picture_url'] = None


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


@only_for_post
def subscribe_to_activity(item):
    """Subscribe to activity happening on a post.

    This allows the post author to know when a comment is posted.
    """
    log.debug('Subscribing user to post %s activity' % item['_id'])
    activity_subscribe(item['user'], 'node', item['_id'])


def after_inserting_posts(items):
    for item in items:
        subscribe_to_activity(item)


@only_for_post
def after_deleting_post(item):
    from pillar.celery import algolia_tasks
    algolia_tasks.algolia_index_node_delete.delay(str(item['_id']))
