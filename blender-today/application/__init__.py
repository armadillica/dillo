from flask import Flask, Blueprint
from flask.ext.sqlalchemy import SQLAlchemy
from flask_mail import Mail

import config

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static')

app.config.from_object(config.Deployment)

db = SQLAlchemy(app)
mail = Mail(app)

from modules.admin import backend
from modules.pages import admin
from modules.users import admin
from modules.main import *
from modules.settings import settings

filemanager = Blueprint('filemanager', __name__, static_folder='static/files')
app.register_blueprint(filemanager)
app.register_blueprint(settings, url_prefix='/settings')

from modules.users.model import user_datastore
