import os
from flask import render_template_string
from application import app

def render_theme_template(path, **kwargs):
    # Build full path to the theme file
    theme_path = os.path.join(app.root_path, 'themes',
        app.config['SETTINGS_THEME'], 'templates', path)
    # If the file is not found, revert to default
    # TODO: support child themes (so that we can look up the fallback file)
    if not os.path.exists(theme_path):
        theme_path = os.path.join(app.root_path, 'themes', 'dillo', 'templates',
            path)
    # Read the content of the file
    with open(theme_path, 'r') as theme_content:
        content = theme_content.read()
    # Render the template and pass over the context
    return render_template_string(content.decode("utf8"), **kwargs)

