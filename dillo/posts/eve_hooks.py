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

from dillo.node_types.post import node_type_post
from pillar.api.nodes import only_for_node_type_decorator

log = logging.getLogger(__name__)
only_for_post = only_for_node_type_decorator(node_type_post['name'])


@only_for_post
def before_creating_post(post):
    post['properties']['rating_positive'] = 0
    post['properties']['rating_negative'] = 0
    post['properties']['hot'] = 0

def before_creating_posts(nodes):
    for node in nodes:
        before_creating_post(node)


def setup_app(app):
    app.on_insert_nodes += before_creating_posts
