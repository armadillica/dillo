from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import StringField

class FormSettings(Form):
    logo_image = FileField('The logo')
    logo_alt = StringField('The image alt tag')
    title = StringField('Dillo title')
    tagline = StringField('Dillo tagline')
