from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import StringField
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms import HiddenField
from wtforms.widgets import HiddenInput
from wtforms.validators import DataRequired
from wtforms.validators import URL
from application.modules.users.model import Role
from application.modules.posts.model import Category
from application.modules.posts.model import PostType
from application.helpers import computed_user_roles


class PostForm(Form):
    category_id = SelectField('Group', coerce=int)
    # post_type_id = SelectField(
    #     'Post type id',
    #     choices=[(t.id, t.name) for t in PostType.query.all()],
    #     widget=HiddenInput
    # )
    post_type_id = HiddenField('Post type id', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content')
    url = StringField('URL')
    picture = FileField('A picture')
    picture_remote = HiddenField('A picture coming from the web')


class CommentForm(Form):
    content = TextAreaField('Content', validators=[DataRequired()])
    parent_id = HiddenField('Parent')


def get_post_form():
    allowed_categories = Category.query \
        .filter(Category.roles.any(Role.id.in_(computed_user_roles()))) \
        .all()
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in allowed_categories]
    return form
