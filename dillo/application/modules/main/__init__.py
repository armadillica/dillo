import os
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import flash
from flask import send_from_directory
from flask import send_file
from flask import abort
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

@app.route('/terms')
def terms():
    return view('terms')

@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

@app.route('/theme-static/<path:filename>')
def theme_static(filename):
    """Return a static file from the static folder in the current theme dir.
    If the file is not found, fall back to the parent theme or the dillo theme.
    """
    theme_path_static = os.path.join(app.root_path, 'themes',
        app.config['SETTINGS_THEME'], 'static', filename)
    if not os.path.exists(theme_path_static):
        # Hardcoded parent theme (fallback if not found)
        father_theme_path_static = os.path.join(app.root_path, 'themes', 'dillo',
            'static', filename)
        if not os.path.exists(father_theme_path_static):
            return abort(404)
    return send_file(theme_path_static)
