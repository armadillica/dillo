from flask_wtf import Form
from wtforms import StringField, FieldList, FormField


class LinkForm(Form):
    name = StringField()
    url = StringField()


class LinksListForm(Form):
    links = FieldList(FormField(LinkForm), min_entries=2, max_entries=5)
