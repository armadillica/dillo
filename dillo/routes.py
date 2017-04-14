import logging

from flask import Blueprint, render_template, redirect, url_for

from pillar.web import system_util

from dillo import current_dillo

blueprint = Blueprint('dillo', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    return redirect(url_for('posts.index'))

