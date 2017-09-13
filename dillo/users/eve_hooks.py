# -*- encoding: utf-8 -*-

"""Hooks for user types.

On post creation:

- set karma

"""

import datetime
import logging
from flask import current_app
from dillo import EXTENSION_NAME


log = logging.getLogger(__name__)


def after_creating_user(user: dict):
    """
    Expand user data with custom dillo fields
    """
    user_id = user['_id']
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    custom_fields = {
        'karma': {
            'positive': 0,
            'negative': 0,
        },
    }

    log.debug('Recording user custom extension_props for dillo')

    db_fieldname = f'extension_props.{EXTENSION_NAME}'
    users_collection = current_app.data.driver.db['users']

    new_user = users_collection.find_one_and_update(
        {'_id': user_id},
        {'$set': {db_fieldname: custom_fields}},
        {db_fieldname: 1},
    )


def after_creating_users(users: list):
    for user in users:
        after_creating_user(user)


def setup_app(app):
    app.on_inserted_users += after_creating_users
