import logging

import flask
from werkzeug.local import LocalProxy
from pillar.extension import PillarExtension

EXTENSION_NAME = 'dillo'


class DilloExtension(PillarExtension):
    def __init__(self):
        self._log = logging.getLogger('%s.DilloExtension' % __name__)

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


def _get_current_dillo():
    """Returns the Dillo extension of the current application."""

    return flask.current_app.pillar_extensions[EXTENSION_NAME]


current_dillo = LocalProxy(_get_current_dillo)
"""Dillo extension of the current app."""
