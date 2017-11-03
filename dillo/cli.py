"""Commandline interface for Dillo."""

import logging

from flask import current_app
from flask_script import Manager

from pillar.api.utils import authentication
from pillar.cli import manager

import dillo.setup
import dillo.api.posts.rating

log = logging.getLogger(__name__)

manager_dillo = Manager(current_app, usage="Perform Dillo operations")

manager.add_command("dillo", manager_dillo)


@manager_dillo.command
@manager_dillo.option('-r', '--replace', dest='replace', action='store_true', default=False)
def setup_for_dillo(project_url, replace=False):
    """Adds Dillo node types to the project.

    Use --replace to replace pre-existing Dillo node types
    (by default already existing Dillo node types are skipped).
    """

    authentication.force_cli_user()
    dillo.setup.setup_for_dillo(project_url, replace=replace)


@manager_dillo.command
def index_nodes_rebuild():
    """Clear all nodes, update settings and reindex all posts."""

    from dillo.api.posts.hooks import algolia_index_post_save

    nodes_index = current_app.algolia_index_nodes

    log.info('Dropping index: {}'.format(nodes_index))
    nodes_index.clear_index()
    index_nodes_update_settings()

    db = current_app.db()
    nodes_dillo_posts = db['nodes'].find({
        '_deleted': {'$ne': True},
        'node_type': 'dillo_post',
        'properties.status': 'published',
    })

    log.info('Reindexing all nodes')
    for post in nodes_dillo_posts:
        algolia_index_post_save(post)


@manager_dillo.command
def process_posts(community_name):
    """Manually trigger pre-update hooks."""
    from flask import g
    from pillar.auth import UserClass
    from dillo.api.posts.hooks import process_picture_oembed, before_replacing_post
    from dillo.setup import _get_project
    project = _get_project(community_name)

    nodes_collection = current_app.db()['nodes']
    user_collection = current_app.db()['users']
    nc = nodes_collection.find({
        'node_type': 'dillo_post',
        'properties.status': 'published',
        'project': project['_id'],
    })

    for n in nc:
        # Log in as doc user
        user_doc = user_collection.find_one({'_id': n['user']})
        u = UserClass.construct(user_doc['_id'], user_doc)
        g.current_user = u

        n_id = n['_id']
        print(f'Processing node {n_id}')
        process_picture_oembed(n, n)
        before_replacing_post(n, n)
        nodes_collection.find_one_and_replace({'_id': n_id}, n)


@manager_dillo.command
def index_nodes_update_settings():
    """Configure indexing backend as required by the project"""
    nodes_index = current_app.algolia_index_nodes

    # Automatically creates index if it does not exist
    nodes_index.set_settings({
        'searchableAttributes': [
            'name',
            'content',
        ],
        'customRanking': [
            'desc(hot)',
            'desc(created)',
        ],
        'attributesForFaceting': [
            'searchable(tags)',
            'project._id',
        ]
    })


@manager_dillo.command
def reset_users_karma():
    """Recalculate the users karma"""
    dillo.api.posts.rating.rebuild_karma()
