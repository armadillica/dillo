import logging

import flask
from werkzeug.local import LocalProxy
from micawber.providers import bootstrap_basic
from micawber.providers import Provider
from pillar.extension import PillarExtension

EXTENSION_NAME = 'dillo'


class DilloExtension(PillarExtension):
    def __init__(self):
        self._log = logging.getLogger('%s.DilloExtension' % __name__)

        self.oembed_registry = bootstrap_basic()
        self.oembed_registry.register(
            'https?://sketchfab.com/models/*',
            Provider('https://sketchfab.com/oembed'))
        self.oembed_registry.register(
            'https?://p3d.in/*',
            Provider('https://p3d.in/oembed'))
        self.oembed_registry.register(
            'https?://instagram.com/p/*',
            Provider('http://api.instagram.com/oembed'))

    @property
    def name(self):
        return EXTENSION_NAME

    def flask_config(self):
        """Returns extension-specific defaults for the Flask configuration.

        Use this to set sensible default values for configuration settings
        introduced by the extension.

        :rtype: dict
        """

        # Just so that it registers the management commands.
        from . import cli

        return {}

    def eve_settings(self):
        """Returns extensions to the Eve settings.

        Currently only the DOMAIN key is used to insert new resources into
        Eve's configuration.

        :rtype: dict
        """

        return {}

    def blueprints(self):
        """Returns the list of top-level blueprints for the extension.

        These blueprints will be mounted at the url prefix given to
        app.load_extension().

        :rtype: list of flask.Blueprint objects.
        """

        from . import routes
        import dillo.posts.routes
        return [
            routes.blueprint,
            dillo.posts.routes.blueprint
        ]

    @property
    def template_path(self):
        import os.path
        return os.path.join(os.path.dirname(__file__), 'templates')

    @property
    def static_path(self):
        import os.path
        return os.path.join(os.path.dirname(__file__), 'static')

    def setup_app(self, app):
        from dillo import posts
        from . import comments

        posts.setup_app(app)
        comments.setup_app(app)

    def activities_for_node(self, node_id, max_results=20, page=1):

        api = pillar_api()
        activities = pillarsdk.Activity.all({
            'where': {
                '$or': [
                    {'object_type': 'node',
                     'object': node_id},
                    {'context_object_type': 'node',
                     'context_object': node_id},
                ],
            },
            'sort': [('_created', -1)],
            'max_results': max_results,
            'page': page,
        }, api=api)

        # Fetch more info for each activity.
        for act in activities['_items']:
            act.actor_user = pillar.web.subquery.get_user_info(act.actor_user)

        return activities


def _get_current_dillo():
    """Returns the Dillo extension of the current application."""

    return flask.current_app.pillar_extensions[EXTENSION_NAME]


current_dillo = LocalProxy(_get_current_dillo)
"""Dillo extension of the current app."""
