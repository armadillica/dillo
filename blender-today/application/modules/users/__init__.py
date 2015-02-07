import datetime

from flask import session
from flask import redirect
from flask import url_for
from flask import request

from flask.ext.security.utils import login_user

from application import app
from application import db
from application import google
from application.modules.users.model import user_datastore


@app.route('/oauth/google/login')
def google_login():
    return google.authorize(callback=url_for('google_authorized', _external=True))

@app.route('/oauth/google/logout')
def google_logout():
    session.pop('google_token', None)
    session.clear()
    return redirect(url_for('index'))

@app.route('/oauth/google/authorized')
def google_authorized():
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )

    print resp
    session['google_token'] = (resp['access_token'], '')
    resp = google.get('userinfo')
    user = user_datastore.get_user(resp.data['email'])
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
        user = user_datastore.create_user(
            email=resp.data['email'],
            active=True,
            first_name=resp.data['name'],
            last_name=resp.data['family_name'],
            current_login_at=datetime.datetime.now(),
            current_login_ip=request.remote_addr,
            login_count=1
            )
        db.session.commit()

    login_user(user)
    return redirect(url_for('index'))


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


@app.route('/oauth/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
