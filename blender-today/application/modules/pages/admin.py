from application import app
from application import db

from application.modules.pages.model import Page

from application.modules.admin import *
from application.modules.admin import _list_thumbnail


# -------- Views --------
class PageView(CustomModelView):
    column_searchable_list = ('title',)
    column_list = ('title', 'picture', 'creation_date')
    column_formatters = { 'picture': _list_thumbnail }
    form_extra_fields = {'picture': image_upload_field}
    form_overrides = dict(content=CKTextAreaField)
    create_template = 'admin/contents/create.html'
    edit_template = 'admin/contents/edit.html'


backend.add_view(PageView(Page, db.session, name='Pages', url='pages'))
