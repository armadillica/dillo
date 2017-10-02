def setup_app(app):
    from . import posts
    from . import users

    posts.setup_app(app)
    users.setup_app(app)
