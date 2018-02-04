from . import hooks


def setup_app(app):
    app.on_inserted_users += hooks.after_creating_users
    app.on_replaced_users += hooks.on_replaced_users