import logging
import bson
from flask import current_app
from . import hooks

log = logging.getLogger(__name__)


def update_links(user_id: bson.ObjectId, links: list):
    """Update the links extension property."""

    from pymongo.results import UpdateResult

    assert isinstance(user_id, bson.ObjectId)

    users_coll = current_app.db('users')
    result: UpdateResult = users_coll.update_one(
        {'_id': user_id},
        {'$set': {'extension_props_public.dillo.links': links}},
    )

    if result.matched_count == 0:
        raise ValueError(f'User {user_id} not found.')


def setup_app(app):
    app.on_inserted_users += hooks.after_creating_users
