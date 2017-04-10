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
from dillo.node_types.post import node_type_post
from dillo.utils.sorting import hot

log = logging.getLogger(__name__)
only_for_post = only_for_node_type_decorator(node_type_post['name'])


def algolia_index_post_save(node):

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': ObjectId(node['project'])})

    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one({'_id': ObjectId(node['user'])})

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
    }
    if 'description' in node and node['description']:
        node_ob['description'] = node['description']
    # Hack for instantsearch.js. Because we can't to string comparison in Hogan, we store this case
    # in a boolean.
    if node['property']['post_type'] == 'link':
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
def after_creating_post(item):
    algolia_index_post_save(item)


def after_creating_posts(items):
    for item in items:
        after_creating_post(item)


@only_for_post
def after_replacing_post(item, original):
    update_hot(item)
    algolia_index_post_save(item)


def setup_app(app):
    app.on_insert_nodes += before_creating_posts
    app.on_replace_nodes += after_replacing_post
    app.on_inserted_nodes += after_creating_posts
