import datetime
import random
import string
from datetime import date
from datetime import timedelta
from sqlalchemy import desc

from flask import session
from flask import redirect
from flask import url_for
from flask import request
from flask import flash
from flask import render_template
from flask import jsonify
from flask import Blueprint
from flask import abort

from flask.ext.security.utils import login_user
from flask.ext.security.signals import user_registered
from flask.ext.security import current_user
from flask_oauthlib.client import OAuthException

from application import app
from application import db
from application import google
from application import facebook
from application import blender_id
from application.modules.users.model import user_datastore
from application.modules.users.model import UserOauth
from application.modules.users.model import UserKarma
from application.modules.users.model import User
from application.modules.posts.model import Post


users = Blueprint('users', __name__)


@user_registered.connect_via(app)
def user_registered_sighandler(sender, **extra):
    user = extra['user']
    user_karma = UserKarma(
        user_id=user.id)
    db.session.add(user_karma)
    db.session.commit()


def check_oauth_provider(provider):
    if not provider:
        return abort(404)


def user_get_or_create(email, first_name, last_name, service, service_user_id):
    user = user_datastore.get_user(email)
    # If user email search fails, we search for the user service id
    if not user:
        user_oauth = UserOauth.query\
            .filter_by(service=service, service_user_id=service_user_id)\
            .first()
        # If we find it, we get the user from the datastore
        if user_oauth:
            user = user_datastore.get_user(user_oauth.user_id)
    # If user exsits, update
    if user:
        user.last_login_at = user.current_login_at
        user.last_login_ip = user.current_login_ip
        user.current_login_at = datetime.datetime.now()
        user.current_login_ip = request.remote_addr
        if user.login_count:
            user.login_count += 1
        else:
            user.login_count = 1
        db.session.commit()
    else:
        # If user does not exist, create and assign roles
        # Generate unique username, by searching for an existing username and
        # progressively increment until a free one is found
        username = email.split("@")[0]
        index = 1
        while User.query.filter_by(username=username).first():
            username = "{0}{1}".format(username, index)
            index += 1

        user = user_datastore.create_user(
            email=email,
            username=username,
            password=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5)),
            active=True,
            first_name=first_name,
            last_name=last_name,
            current_login_at=datetime.datetime.now(),
            current_login_ip=request.remote_addr,
            login_count=1
            )
        db.session.commit()

        user_oauth = UserOauth(
            user_id=user.id,
            service=service,
            service_user_id=service_user_id)
        db.session.add(user_oauth)

        user_karma = UserKarma(
            user_id=user.id)
        db.session.add(user_karma)
        db.session.commit()

    return user


@app.route('/oauth/google/login')
def google_login():
    check_oauth_provider(google)
    return google.authorize(callback=url_for('google_authorized', _external=True))


@app.route('/oauth/google/logout')
def google_logout():
    check_oauth_provider(google)
    session.pop('google_token', None)
    session.clear()
    return redirect(url_for('index'))


@app.route('/oauth/google/authorized')
def google_authorized():
    check_oauth_provider(google)
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )

    session['google_token'] = (resp['access_token'], '')
    resp = google.get('userinfo')

    user = user_get_or_create(
        resp.data['email'],
        resp.data['given_name'],
        resp.data['family_name'],
        'google',
        resp.data['email'])

    if user.is_active:
        login_user(user, remember=True)
    elif user.deleted:
        flash('This username has been deleted')
    else:
        flash('This account is disabled')
    return redirect(url_for('index'))

if google:
    @google.tokengetter
    def get_google_oauth_token():
        return session.get('google_token')


@app.route('/oauth/facebook/login')
def facebook_login():
    check_oauth_provider(facebook)
    callback = url_for(
        'facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    return facebook.authorize(callback=callback)


@app.route('/oauth/facebook/authorized')
def facebook_authorized():
    check_oauth_provider(facebook)
    resp = facebook.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: %s' % resp.message

    session['facebook_oauth_token'] = (resp['access_token'], '')
    resp = facebook.get('/me')

    user = user_get_or_create(
        resp.data['email'],
        resp.data['first_name'],
        resp.data['last_name'],
        'facebook',
        resp.data['id'])

    if user.is_active:
        login_user(user, remember=True)
    elif user.deleted:
        flash('This username has been deleted')
    else:
        flash('This account is disabled')
    return redirect(url_for('index'))

if facebook:
    @facebook.tokengetter
    def get_facebook_oauth_token():
        return session.get('facebook_oauth_token')


@app.route('/oauth/blender-id/login')
def blender_id_login():
    check_oauth_provider(blender_id)
    callback = url_for(
        'blender_id_authorized',
        next=None,
        _external=True
    )
    return blender_id.authorize(callback=callback)


@app.route('/oauth/blender-id/authorized')
def blender_id_authorized():
    check_oauth_provider(blender_id)
    resp = blender_id.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: %s' % resp.message

    session['blender_id_oauth_token'] = (resp['access_token'], '')
    resp = blender_id.get('user')

    user = user_get_or_create(
        resp.data['email'],
        resp.data['first_name'],
        resp.data['last_name'],
        'blender-id',
        resp.data['id'])

    if user.is_active:
        login_user(user, remember=True)
    elif user.deleted:
        flash('This username has been deleted')
        return redirect(url_for('index'))
    else:
        flash('This account is disabled')
        return redirect(url_for('index'))

    # Update or create roles
    for role, is_assigned in resp.data['roles'].items():
        r = user_datastore.find_or_create_role(role)
        if is_assigned:
            user_datastore.add_role_to_user(user, r)
        else:
            user_datastore.remove_role_from_user(user, r)
    db.session.commit()

    if not user.first_name or not user.last_name:
        if not user.username:
            flash('Please set your first and last name or pick a username')
            return redirect(url_for('settings.profile'))

    return redirect(url_for('index'))

if blender_id:
    @blender_id.tokengetter
    def get_blender_id_oauth_token():
        return session.get('blender_id_oauth_token')


@app.route('/oauth/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@users.route('/<int:user_id>')
def view(user_id):
    user = User.query.get_or_404(user_id)
    user_string_id = 'ANONYMOUS'
    if current_user.is_authenticated():
        user_string_id = current_user.string_id
    posts = Post.query\
        .filter_by(user_id=user.id)\
        .filter(Post.status != 'deleted')\
        .order_by(desc(Post.creation_date))\
        .all()
    return render_template('users/view.html', title='user_view',
                           user_string_id=user_string_id, posts=posts,
                           user=user)


@users.route('/stats')
def stats():
    """Query the amount of total users in the last 7 days
    """
    import sqlalchemy as sa
    d = date.today() - timedelta(days=7)
    stats = User.query.with_entities(User.signup_date, sa.func.count(User.signup_date))\
        .filter(User.signup_date > d)\
        .group_by(sa.func.day(User.signup_date))\
        .all()

    return jsonify(stats=stats)
