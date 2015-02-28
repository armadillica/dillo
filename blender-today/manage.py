from flask.ext.script import Manager
from flask.ext.migrate import Migrate
from flask.ext.migrate import MigrateCommand
from application import app
from application import db
from application.modules.posts.model import Post
from application.modules.posts.model import PostRating
from application.helpers import encode_id

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def create_all_tables():
    db.create_all()

@manager.command
def runserver():
    import os
    os.environ['DEBUG'] = 'true'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    app.run()

@manager.command
def populate_for_testing():
    for x in range(50):
        post = Post(
            user_id=1,
            category_id=1,
            post_type_id=1,
            title='test '+str(x),
            slug='the-slug',
            content='<p>content</p>')
        db.session.add(post)
        db.session.commit()
        post.uuid = encode_id(post.id)
        db.session.commit()
        post_rating = PostRating(
            post_id=post.id,
            positive=0,
            negative=0
            )
        db.session.add(post_rating)
        post.update_hot()
        db.session.commit()
        print x


manager.run()
