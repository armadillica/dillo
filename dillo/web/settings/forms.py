from flask_wtf import Form
from flask_wtf.html5 import URLField
from wtforms import StringField, FieldList, FormField
from wtforms.validators import URL, DataRequired


class LinkForm(Form):
    name = StringField('Name', validators=[DataRequired()])
    url = URLField(validators=[DataRequired(), URL()])


class LinksListForm(Form):
    links = FieldList(FormField(LinkForm), max_entries=5)
