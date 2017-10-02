def setup_app(app):
    from . import comments
    from . import posts
    from . import users

    comments.setup_app(app)
    posts.setup_app(app)
    users.setup_app(app)
