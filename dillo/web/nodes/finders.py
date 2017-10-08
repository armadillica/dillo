import logging
from flask import url_for

from pillar.web.nodes.finders import register_node_finder


log = logging.getLogger(__name__)


@register_node_finder('dillo_post')
def find_for_dillo_post(project, node):
    """Returns url for a dillo_post."""
    return url_for('posts.view', community_url=project['url'],
                   post_shortcode=node['properties']['shortcode'])
