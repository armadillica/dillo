import logging

from flask import Blueprint,render_template

from pillar.web import system_util

from dillo import current_dillo

blueprint = Blueprint('dillo', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    api = system_util.pillar_api()
    from flask import redirect, url_for
    #return redirect(url_for('index'))
    return render_template('dillo/index.pug')


