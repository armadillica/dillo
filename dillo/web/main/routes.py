import logging

from flask import Blueprint, redirect, url_for, jsonify, render_template
from flask_login import login_required, current_user
from bson import ObjectId


from pillar import current_app

blueprint = Blueprint('dillo', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    return redirect(url_for('posts.index_all'))


@blueprint.route('/privacy')
def privacy():
    return render_template('privacy.html')


@blueprint.route('/about')
def about():
    return render_template('about.html')
