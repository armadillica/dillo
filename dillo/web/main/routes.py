import logging

from flask import Blueprint, redirect, url_for, render_template

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
