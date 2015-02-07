from flask import render_template, redirect, url_for, request, flash
from flask.ext.security import login_required

from application import app
from application.modules.pages import view


# Views
@app.route('/about')
def about():
    return view('about')

@app.route('/')
def homepage():
    return view('about')
