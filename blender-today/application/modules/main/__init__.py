from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import flash

from flask.ext.security import login_required

from application import app
from application.modules.pages import view


# Views
@app.route('/about')
def about():
    return view('about')

@app.route('/')
def index():
    return redirect(url_for('posts.index'))

@app.route('/faq')
def faq():
    return view('faq')