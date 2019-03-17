from . import hooks
from . import rating
from .routes import blueprint_api


def setup_app(app, api_prefix):
    app.on_insert_nodes += hooks.before_inserting_posts
    app.on_inserted_nodes += hooks.after_inserting_posts
    app.on_replace_nodes += hooks.process_picture_oembed
    app.on_replace_nodes += hooks.before_replacing_post
    app.on_fetched_item_nodes += hooks.enrich

    app.register_api_blueprint(blueprint_api, url_prefix=api_prefix)
