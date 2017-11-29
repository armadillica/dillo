from . import hooks


def setup_app(app):
    app.on_inserted_nodes += hooks.after_creating_comments

