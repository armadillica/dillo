from flask import Flask
from flask import session
from flask import Blueprint

from flask.ext.sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_oauthlib.client import OAuth


import config

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static')

app.config.from_object(config.Deployment)

db = SQLAlchemy(app)
mail = Mail(app)
oauth = OAuth(app)

# Config at https://console.developers.google.com/
google = oauth.remote_app(
    'google',
    consumer_key=app.config.get('SOCIAL_GOOGLE')['consumer_key'],
    consumer_secret=app.config.get('SOCIAL_GOOGLE')['consumer_secret'],
    request_token_params={
        'scope': 'https://www.googleapis.com/auth/userinfo.email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)



from modules.admin import backend
from modules.pages import admin
from modules.users import admin
from modules.main import *
from modules.settings import settings

filemanager = Blueprint('filemanager', __name__, static_folder='static/files')
app.register_blueprint(filemanager)
app.register_blueprint(settings, url_prefix='/settings')

from modules.users.model import user_datastore
