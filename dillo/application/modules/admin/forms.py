from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import StringField
from wtforms import TextAreaField

class FormSettings(Form):
    logo_image = FileField('Site logo')
    logo_alt = StringField('Logo alternative text')
    favicon = FileField('Favicon')
    title = StringField('Site title')
    title_html = StringField('Site title with HTML tags')
    tagline = StringField('Tagline')
    footer = TextAreaField('Footer')
    credits = StringField('Site credits')
