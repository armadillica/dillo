def setup_app(app):
    from . import comments
    from . import posts
    from . import users

    comments.setup_app(app)
    posts.setup_app(app, api_prefix='/posts')
    users.setup_app(app)
