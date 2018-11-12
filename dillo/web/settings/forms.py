import wtforms
from wtforms.validators import URL, DataRequired, Email
from flask_wtf import Form
from flask_wtf.html5 import URLField, EmailField

from pillar.web.users import forms


class LinkForm(wtforms.Form):
    name = wtforms.StringField('Name', validators=[DataRequired()])
    url = URLField(validators=[DataRequired(), URL()])


class LinksListForm(Form):
    links = wtforms.FieldList(wtforms.FormField(LinkForm), max_entries=5)


class UserProfileForm(forms.UserProfileForm):
    full_name = wtforms.StringField('Full Name', validators=[DataRequired()])
    email = EmailField(validators=[DataRequired(), Email()])
