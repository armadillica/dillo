from application import app
from application import db

from application.modules.posts.model import Post
from application.modules.admin import *


# -------- Views --------
class PostView(CustomModelView):
    column_searchable_list = ('title',)
    column_list = ('title', 'uuid', 'creation_date')
    form_overrides = dict(content=CKTextAreaField)
    create_template = 'admin/contents/create.html'
    edit_template = 'admin/contents/edit.html'


backend.add_view(PostView(Post, db.session, name='Posts', url='posts'))
