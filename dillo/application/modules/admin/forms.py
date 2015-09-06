from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import StringField
from wtforms import TextAreaField

class FormSettings(Form):
    logo_image = FileField('The logo')
    logo_alt = StringField('The image alt tag')
    title = StringField('Dillo title')
    title_html = StringField('Dillo title with HTML tags')
    tagline = StringField('Dillo tagline')
    footer = TextAreaField('Footer')
    credits = StringField('Site credits')
