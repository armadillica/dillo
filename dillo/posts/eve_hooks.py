# -*- encoding: utf-8 -*-

"""Hooks for posts types.

On post creation:

- set rating
- calculate hot value
- set AID
- set slug from title

"""

import itertools
import logging
import datetime
from bson import ObjectId
from flask import current_app
from pillar.api.file_storage import generate_link
from pillar.api.nodes import only_for_node_type_decorator
from pillar.api.utils.authentication import current_user_id
from dillo.node_types.post import node_type_post
from dillo.utils.sorting import hot

log = logging.getLogger(__name__)
only_for_post = only_for_node_type_decorator(node_type_post['name'])


def algolia_index_post_save(node):

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': ObjectId(node['project'])})

    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one({'_id': ObjectId(node['user'])})

    rating = node['properties']['rating_positive'] - node['properties']['rating_negative']

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
        'rating': rating,
    }
    if 'description' in node and node['description']:
        node_ob['description'] = node['description']
    # Hack for instantsearch.js. Because we can't to string comparison in Hogan, we store this case
    # in a boolean.
    if node['properties']['post_type'] == 'link':
        node_ob['is_link'] = True
    if 'picture' in node and node['picture']:
        files_collection = current_app.data.driver.db['files']
        lookup = {'_id': ObjectId(node['picture'])}
        picture = files_collection.find_one(lookup)
        if picture['backend'] == 'gcs':
            variation_t = next((item for item in picture['variations'] \
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
def before_creating_post(item):
    item['properties']['rating_positive'] = 0
    item['properties']['rating_negative'] = 0
    update_hot(item)


def before_creating_posts(items):
    for item in items:
        before_creating_post(item)


@only_for_post
def after_replacing_post(item, original):
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
    app.on_replace_nodes += after_replacing_post
    app.on_fetched_item_nodes += enrich
