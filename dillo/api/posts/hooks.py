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
from pillar.api.nodes.eve_hooks import only_for_node_type_decorator
from pillar.api.utils.authentication import current_user_id
from pillar.api.file_storage import upload_and_process
from pillar.api.activities import activity_subscribe
from pillar.api.utils import utcnow
from dillo import current_dillo
from dillo.node_types.post import node_type_post
from dillo.utils.sorting import hot
from dillo.shortcodes import generate_shortcode

log = logging.getLogger(__name__)
only_for_post = only_for_node_type_decorator(node_type_post['name'])


def update_hot(item):
    """Update hot value for a Post.

    The calculation of hotness is calculated in different ways, depending on the
    type of Post. In the case of upvotable posts, we calculate it based on
    '_created', 'rating_positive' and 'rating_negative'.
    In the case of documents featuring a 'download' and a 'download_updated'
    property, we use 'download_updated' instead of '_created'.
    """

    item_properties = item['properties']

    # Default values for rating
    rating_positive = 1
    rating_negative = 0

    if 'download' in item_properties and 'download_updated' in item_properties:
        # We are dealing with a post featuring a downloadable item
        dt = item_properties['download_updated']
    else:
        # Usually text or link posts, votable
        dt = item['_created']
        rating_positive = item_properties['rating_positive']
        rating_negative = item_properties['rating_negative']

    dt = dt.replace(tzinfo=datetime.timezone.utc)

    item_properties['hot'] = hot(
        rating_positive,
        rating_negative,
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
    item['permissions'] = {'users': [{'user': current_user_id(), 'methods': ['PUT', 'DELETE']}]}


def before_inserting_posts(items):
    for item in items:
        set_defaults(item)


def convert_to_markdown(item):
    """Convert content from Markdown to HTML."""
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


def check_download_property_update(item, original):
    """Update node if properties.download was updated.

    In particular, reset the downloads_latest to 0 and update hotness.
    The hotness is updated based on _updated and not _created.
    """
    if 'download' not in item['properties'] or 'download' not in original['properties']:
        return

    if item['properties']['download'] != original['properties'].get('download'):
        item['properties']['downloads_latest'] = 0
        # Update the upload timestamp
        item['properties']['download_updated'] = utcnow()
        # Hotness recalculation is done in 'before_replacing_post'


@only_for_post
def before_replacing_post(item, original):
    if len(item['properties']['content']) < 6:
        log.debug('Content must be longer than 7 chars')
        return abort(422)
    status_original = original['properties']['status']
    status_updated = item['properties']['status']
    if status_updated == 'draft':
        if status_original in {'pending', 'draft'}:
            pass
        else:
            log.debug('Published posts can not be unpublished')
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
        log.debug('The following status transition is not allowed: %s -> %s' % (
            status_original, status_updated))
        return abort(422)

    post_handler = {
        'link': generate_oembed,
        'text': convert_to_markdown,
    }

    handler = post_handler[item['properties']['post_type']]
    handler(item)
    # Ensure that comments count was not modified
    if 'comments_count' in original['properties']:
        item['properties']['comments_count'] = original['properties']['comments_count']
    elif 'comments_count' in item['properties']:
        # If no comments_count was specified in the original document, strip comments_count from
        # the updated document.
        del item['properties']['comments_count']
    check_download_property_update(item, original)
    update_hot(item)


@only_for_post
def process_picture_oembed(item, original):
    """If picture_oembed is specified, download the image and populate the picture property."""
    picture_url = item['properties'].get('picture_url')
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
