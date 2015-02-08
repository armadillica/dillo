from flask_wtf import Form
from wtforms import StringField
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms.validators import DataRequired

class PostForm(Form):
    category_id = SelectField('Group', coerce=int)
    post_type_id = SelectField('Post Type', coerce=int)
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])

class CommentForm(Form):
    content = TextAreaField('Content', validators=[DataRequired()])
