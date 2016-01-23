import os
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
    app.config['SETTINGS_LOGO_IMAGE'] = '/static/images/' + app.config['SETTINGS_LOGO_IMAGE']
    app.config['SETTINGS_FAVICON'] = '/static/images/' + app.config['SETTINGS_FAVICON']


    # Enable custom templates and static folder (a theme folder should be
    # placed in the 'themes' folder in the root of the application).
    if app.config['SETTINGS_THEME'] != 'dillo':
        root_static = os.path.split(app.static_folder)[0]
        app.static_folder = os.path.join(root_static, 'themes',
            app.config['SETTINGS_THEME'], 'static')
        root_template = os.path.split(app.template_folder)[0]
        app.template_folder = os.path.join(root_static, 'themes',
            app.config['SETTINGS_THEME'], 'templates')
