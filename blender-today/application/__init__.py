from flask import Flask
from flask import session
from flask import Blueprint

from flask.ext.sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_oauthlib.client import OAuth
from imgurpython import ImgurClient

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

facebook = oauth.remote_app(
    'facebook',
    consumer_key=app.config.get('SOCIAL_FACEBOOK')['app_id'],
    consumer_secret=app.config.get('SOCIAL_FACEBOOK')['app_secret'],
    request_token_params={'scope': 'email'},
    base_url='https://graph.facebook.com',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth'
)


blender_id = oauth.remote_app(
    'blender_id',
    consumer_key=app.config.get('SOCIAL_BLENDER_ID')['app_id'],
    consumer_secret=app.config.get('SOCIAL_BLENDER_ID')['app_secret'],
    request_token_params={'scope': 'email'},
    base_url=app.config['BLENDER_ID_BASE_URL'],
    request_token_url=None,
    access_token_url=app.config['BLENDER_ID_BASE_ACCESS_TOKEN_URL'],
    authorize_url=app.config['BLENDER_ID_AUTHORIZE_URL']
)

imgur_client = ImgurClient(app.config['IMGUR_CLIENT_ID'], app.config['IMGUR_CLIENT_SECRET'])

from modules.admin import backend
from modules.pages import admin
from modules.users import admin
from modules.main import *
from modules.posts import posts
from modules.posts import admin
from modules.settings import settings
from modules.comments import comments

filemanager = Blueprint('filemanager', __name__, static_folder='static/files')
app.register_blueprint(filemanager)
app.register_blueprint(settings, url_prefix='/settings')
app.register_blueprint(posts)
app.register_blueprint(comments, url_prefix='/comments')

from modules.users.model import user_datastore
