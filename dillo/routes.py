import logging

from flask import Blueprint,render_template

from pillar.web import system_util

from dillo import current_dillo

blueprint = Blueprint('dillo', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    api = system_util.pillar_api()
    return render_template('dillo/index.pug')


@blueprint.route('/search')
def search():
    return render_template('dillo/search.pug')


