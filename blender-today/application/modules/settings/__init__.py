from flask import request
from flask import Blueprint
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import flash
from flask import abort
from flask import jsonify

from flask.ext.security import login_required
from flask.ext.security import current_user
from flask.ext.security import logout_user

from application import app
from application import db
from application.modules.settings.forms import ProfileForm
from application.modules.users.model import user_datastore, User


settings = Blueprint('settings', __name__)

# Views
@settings.route('/', methods=('GET', 'POST'))
@login_required
def profile():
    # Initialize the profile form, preloading existing data
    form = ProfileForm(
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username
        )

    # If the form is submitted via POST and is succesfully validated
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.username = form.username.data

        if not current_user.first_name or not current_user.last_name:
            if not current_user.username:
                flash('Please set your first and last name or pick a username')
                return redirect(url_for('settings.profile'))
                # return jsonify(
                #     error=400,
                #     message=str('Please set your first and last name or pick a username')), 400
        db.session.commit()
        flash('Profile updated!')

    return render_template('settings/profile.html', 
        form=form,
        title='settings_profile')


@settings.route('/account')
@login_required
def account():
    return render_template('settings/account.html', 
        title='settings_account')


@settings.route('/delete')
@login_required
def delete():
    current_user.deleted = True
    user_datastore.deactivate_user(current_user)
    logout_user()
    db.session.commit()
    flash('Goodbye! We are sorry to see you go!')
    return redirect(url_for('index'))

# TODO(fsiddi): Handle primary and seconday emails
#
# @settings.route('/email')
# def email():
#     page = Page.query.filter_by(url='about').one()
#     return render_template('settings/email.html', 
#         content=page.content,
#         title='settings_email')

