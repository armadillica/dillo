import os
import jinja2
from application import app
from application import db
from application.modules.admin.model import Setting

def load_settings():
    """Load the application settings from the Settings table in the database
    in the app config.
    """
    settings = dict(
        logo_alt='Dillo',
        logo_image='dillogo.png',
        favicon='favicon.png',
        title='Dillo',
        title_html='Dillo',
        tagline='The open conversation platform',
        footer='',
        credits='',
        keywords='news, community, open source',
        twitter_username='dillospace',
        theme='dillo'
        )

    for setting_name, setting_value in settings.iteritems():
        s = Setting.query.filter_by(name=setting_name).first()
        if not s:
            # If the queried setting is missing, create one with empty value
            s = Setting(name=setting_name,
                value=setting_value,
                data_type='str')
            db.session.add(s)
            db.session.commit()

        config_key = 'SETTINGS_' + setting_name.upper()
        app.config[config_key] = s.value

    # Extra update for the logo image path
    app.config['SETTINGS_LOGO_IMAGE'] = '/theme-static/images/' + app.config['SETTINGS_LOGO_IMAGE']
    app.config['SETTINGS_FAVICON'] = '/theme-static/images/' + app.config['SETTINGS_FAVICON']

    # Enable custom templates (a theme folder should be placed in the 'themes'
    # folder in the root of the application).
    theme_path = os.path.join(app.root_path, 'themes',
        app.config['SETTINGS_THEME'], 'templates')

    # Hardcoded parent theme for every other theme (later this can be configured)
    parent_theme_path = os.path.join(app.root_path, 'themes', 'dillo', 'templates')

    paths_list = [
        jinja2.FileSystemLoader(theme_path),
        jinja2.FileSystemLoader(parent_theme_path),
        app.jinja_loader
    ]

    # Set up a custom loader, so that Jinja searches for a theme file first in
    # the current theme dir, and if it fails it searches in the default location.
    custom_jinja_loader = jinja2.ChoiceLoader(paths_list)
    app.jinja_loader = custom_jinja_loader
