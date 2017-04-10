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
from flask import current_app

from pillar.api.nodes import only_for_node_type_decorator
from dillo.node_types.post import node_type_post
from dillo.utils.sorting import hot

log = logging.getLogger(__name__)
only_for_post = only_for_node_type_decorator(node_type_post['name'])


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


def setup_app(app):
    app.on_insert_nodes += before_creating_posts
    app.on_replace_nodes += after_replacing_post
