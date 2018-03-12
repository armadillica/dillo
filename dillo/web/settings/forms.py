import wtforms
from wtforms.validators import URL, DataRequired
from flask_wtf import Form
from flask_wtf.html5 import URLField


class LinkForm(wtforms.Form):
    name = wtforms.StringField('Name', validators=[DataRequired()])
    url = URLField(validators=[DataRequired(), URL()])


class LinksListForm(Form):
    links = wtforms.FieldList(wtforms.FormField(LinkForm), max_entries=5)
