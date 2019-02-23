def setup_app(app):
    from . import comments
    from . import posts
    from . import users
    from . import communitites

    comments.setup_app(app)
    posts.setup_app(app, api_prefix='/posts')
    users.setup_app(app)
    communitites.setup_app(app, api_prefix='/communities')
