def setup_app(app):
    from . import users

    users.setup_app(app)
