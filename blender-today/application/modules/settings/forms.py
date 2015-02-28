from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired

class ProfileForm(Form):
    email = StringField('Email', validators=[DataRequired()])
    first_name = StringField('First name')
    last_name = StringField('Last name')
    username = StringField('Username')
