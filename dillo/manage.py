from flask.ext.script import Manager
from flask.ext.migrate import Migrate
from flask.ext.migrate import MigrateCommand
from application import app
from application import db
from application.modules.users.model import user_datastore
from application.modules.users.model import UserKarma
from application.modules.posts.model import Category
from application.modules.posts.model import PostType
from application.modules.admin.model import Setting


migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def setup():
    import getpass
    from flask_security.utils import encrypt_password
    print("Please input the user data for the admin (you can edit later)")
    while True:
        admin_username = raw_input('Admin username:')
        if len(admin_username) < 1:
            print ("Username is too short")
        elif user_datastore.find_user(username=admin_username):
            print ("Username already in use")
        else:
            break
    while True:
        admin_password = getpass.getpass('Admin password:')
        if len(admin_password) < 5:
            print ("Password is too short")
        else:
            break
    while True:
        admin_email = raw_input('Admin email:')
        if user_datastore.find_user(email=admin_email):
            print ("Email aready in use")
        else:
            break
    admin_role = user_datastore.find_or_create_role('admin')
    admin = user_datastore.create_user(
        username=admin_username,
        password=encrypt_password(admin_password),
        email=admin_email)
    db.session.commit()
    user_datastore.add_role_to_user(admin, admin_role)
    db.session.commit()
    # Add karma for the admin
    user_karma = UserKarma(
        user_id=admin.id)
    db.session.add(user_karma)
    db.session.commit()
    print("Admin user succesfully created!")
    # Add default category
    category_default = Category(
        name='News',
        url='news',
        order=0)
    db.session.add(category_default)
    db.session.commit()
    print("Added default News category")
    # Add default post types
    post_types = ['link', 'post']
    for t in post_types:
        post_type = PostType(
            name=t,
            url=t)
        db.session.add(post_type)
        db.session.commit()
        print("Added post type {0}".format(t))


@manager.command
def runserver():
    import os
    os.environ['DEBUG'] = 'true'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    import config
    PORT = config.Deployment.PORT
    HOST = config.Deployment.HOST
    app.run(
        port=PORT,
        host=HOST)


manager.run()
