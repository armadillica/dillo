from . import hooks
from . import rating


def setup_app(app):
    app.on_insert_nodes += hooks.before_creating_posts
    app.on_replace_nodes += hooks.process_picture_oembed
    app.on_replace_nodes += hooks.before_replacing_post
    app.on_fetched_item_nodes += hooks.enrich
