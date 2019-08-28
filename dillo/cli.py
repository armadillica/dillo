"""Commandline interface for Dillo."""

import logging
from bson import ObjectId

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
def setup_db(admin_email):
    """Extends Pillar setup_db."""
    from pillar.cli.setup import setup_db as pillar_setup_db
    # Define the dillo_user_main group, which is automatically assigned
    # after every user creation.
    g = {'name': 'dillo_user_main'}
    current_app.post_internal('groups', g)
    # Execute the default user creation
    pillar_setup_db(admin_email)


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
def reset_users_karma():
    """Recalculate the users karma"""
    dillo.api.posts.rating.rebuild_karma()


@manager_dillo.command
def attach_post_additional_properties():
    """If POST_ADDITIONAL_PROPERTIES exists, extend dillo_post node type.

    See index.md for documentation.
    """

    if not current_app.config['POST_ADDITIONAL_PROPERTIES']:
        log.info('No POST_ADDITIONAL_PROPERTIES was defined')
        return
    # Create a dict with the additional properties ready to be appended to the doc
    db = current_app.db()
    for k, v in current_app.config['POST_ADDITIONAL_PROPERTIES'].items():
        prop_key = f'node_types.$.dyn_schema.{k}'
        form_key = f'node_types.$.form_schema.{k}'
        additional_properties = {prop_key: v['schema']}
        additional_form_schema = {form_key: v['form_schema']} if 'form_schema' in v else None

        for project_id in v['projects']:
            node_type_query = {
                'node_types.name': 'dillo_post',
                '_deleted': {'$ne': True},
                '_id': ObjectId(project_id)}
            u = db['projects'].update_one(
                node_type_query,
                {'$set': additional_properties})
            if additional_form_schema:
                # Update form_schema if a value is specified
                u = db['projects'].update_one(
                    node_type_query,
                    {'$set': additional_form_schema})
            else:
                # Remove the key from form_schema if not specified
                u = db['projects'].update_one(
                    node_type_query,
                    {'$unset': {form_key: ''}})

            if u.modified_count > 0:
                log.info('Updated document')


@manager_dillo.command
def update_post_comments_count():
    """Iterate over every published post and update properties.comments_count."""

    from dillo.api.comments.hooks import update_post_comments_count

    nodes_collection = current_app.db()['nodes']
    posts = nodes_collection.find({
        'node_type': 'dillo_post',
        'properties.status': 'published',
        '_deleted': {'$ne': True},
    })

    post_count = 0
    for post in posts:
        print(f"Updating post {post['_id']} - {post['name']}")
        update_post_comments_count(post['_id'])
        post_count += 1
    print(f"Done! Updated {post_count} posts.")


@manager_dillo.command
def remove_deleted_files():
    """Iterate over every _deleted file, remove file from the system and delete doc."""
    from pillar.api.file_storage_backends import default_storage_backend
    from pillar.api.file_storage_backends.local import LocalBlob

    file_collection = current_app.db()['files']
    files = file_collection.find({
        '_deleted': True
    })

    for f in files:
        bucket = default_storage_backend(f['project'])
        blob = bucket.get_blob(f['name'])
        if not isinstance(blob, LocalBlob):
            log.info('Skipping non local blob')
            continue
        file_abspath = blob.abspath()
        log.info('Removing %s from filesystem' % file_abspath)
        try:
            file_abspath.unlink()
        except OSError:
            log.error('File %s not found' % file_abspath)
        log.info('Deleting file document for file %s' % f['_id'])
        file_collection.delete_one({'_id': f['_id']})
