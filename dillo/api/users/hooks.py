"""Hooks for user types.

On post creation:

- assign to dillo_user_main
- set karma

"""

import logging
from flask import current_app
from pillar.api.users import add_user_to_group

from dillo import EXTENSION_NAME


log = logging.getLogger(__name__)


def add_extension_props(user: dict):
    """Expand user data with custom dillo fields."""
    user_id = user['_id']

    custom_fields = {
        'karma': 0,
    }

    log.debug('Recording user custom extension_props for dillo')

    db_fieldname = f'extension_props.{EXTENSION_NAME}'
    users_collection = current_app.data.driver.db['users']

    users_collection.find_one_and_update(
        {'_id': user_id},
        {'$set': {db_fieldname: custom_fields}},
    )


def assign_to_user_main(user_doc: dict):
    """Make every user create part of the user_main group."""

    groups_coll = current_app.db().groups
    group_dillo_user_main = groups_coll.find_one({'name': 'dillo_user_main'})
    add_user_to_group(user_id=user_doc['_id'], group_id=group_dillo_user_main['_id'])


def after_creating_users(user_docs: list):
    for user_doc in user_docs:
        assign_to_user_main(user_doc)
        add_extension_props(user_doc)
