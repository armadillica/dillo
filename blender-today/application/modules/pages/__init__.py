from flask import render_template
from flask import Blueprint

from application import app
from application import db

from application.modules.pages.model import Page

pages = Blueprint('pages', __name__)

# Views
@pages.route('/<url>')
def view(url):
    page = Page.query.filter_by(url=url).one()
    return render_template('pages/view.html', 
        content=page.content,
        title=page.url)
