def setup_app(app):
    from . import eve_hooks
    from . import rating

    eve_hooks.setup_app(app)
