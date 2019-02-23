from .routes import blueprint_api


def setup_app(app, api_prefix):

    app.register_api_blueprint(blueprint_api, url_prefix=api_prefix)
