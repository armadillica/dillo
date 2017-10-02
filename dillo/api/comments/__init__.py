from . import hooks


def setup_app(app):
    app.on_inserted_nodes += hooks.activity_after_creating_nodes

