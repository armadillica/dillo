import os, hashlib, time
import os.path as op
from werkzeug import secure_filename
from jinja2 import Markup
from wtforms import fields, validators, widgets
from wtforms.fields import SelectField, TextField
from flask import render_template, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext import admin, login
from flask.ext.admin import Admin, expose
from flask.ext.admin import form
from flask.ext.admin.contrib import sqla
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.base import BaseView
from flask.ext.security import current_user
from application import app, db
from application.modules.users.model import user_datastore, User
from application.modules.pages.model import Page
from application.modules.admin.forms import FormLogo
from application.modules.admin.model import Setting



# -------- Utilities to upload and present images --------
def _list_items(view, context, model, name):
    if not model.name:
        return ''
    return Markup(
        '<div class="select2-container-multi">'
            '<ul class="select2-choices" style="border:0;cursor:default;background:none;">%s</ul></div>' % (
                ''.join( ['<li class="select2-search-choice" style="padding:3px 5px;">'
                            '<div>'+item.name+'</div></li>' for item in getattr(model,name)] )))


def _list_thumbnail(view, context, model, name):
    if not getattr(model,name):  #model.name only does not work because name is a string
        return ''
    return Markup('<img src="%s">' % url_for('filemanager.static', filename=form.thumbgen_filename(getattr(model,name))))


# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), '../../static/files',)
try:
    os.mkdir(file_path)
except OSError:
    pass

def prefix_name(obj, file_data):
    # Collect name and extension
    parts = op.splitext(file_data.filename)
    # Get current time (for unique hash)
    timestamp = str(round(time.time()))
    # Has filename only (not extension)
    file_name = secure_filename(timestamp + '%s' % parts[0])
    # Put them together
    full_name = hashlib.md5(file_name).hexdigest() + parts[1]
    return full_name


image_upload_field = form.ImageUploadField('Image',
                    base_path=file_path,
                    thumbnail_size=(100, 100, True),
                    namegen=prefix_name,
                    endpoint='filemanager.static')


# Define wtforms widget and field
class CKTextAreaWidget(widgets.TextArea):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(fields.TextAreaField):
    widget = CKTextAreaWidget()


# Create customized views with access restriction
class CustomModelView(ModelView):
    def is_accessible(self):
        return login.current_user.has_role('admin')

class CustomBaseView(BaseView):
    def is_accessible(self):
        return login.current_user.has_role('admin')


# Create customized index view class that handles login & registration
class CustomAdminIndexView(admin.AdminIndexView):
    def is_accessible(self):
        return login.current_user.has_role('admin')

    @expose('/', methods=['GET','POST'])
    def index(self):
        logo_alt = Setting.query.filter_by(name='logo_alt').first()
        form_logo = FormLogo(
            logo_alt=logo_alt.value)
        return self.render('admin/index.html',
            form_logo=form_logo)

    @expose('/settings', methods=['GET','POST'])
    def settings(self):
        form_logo = FormLogo()
        if form_logo.validate_on_submit():
            logo_alt = Setting.query.filter_by(name='logo_alt').first()
            logo_alt.value = form_logo.logo_alt.data
            if form_logo.logo_image.data:
                # If the user uploads an image from the form
                filename = secure_filename(form_logo.logo_image.data.filename)
                filepath = os.path.join(app.config['STATIC_IMAGES'], filename)
                form_logo.logo_image.data.save(filepath)
                logo_image = Setting.query.filter_by(name='logo_image').first()
                logo_image.value = filename
            db.session.commit()

        return redirect(url_for('admin.index'))

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('index'))


# Create admin
backend = Admin(
    app,
    'Blender Today',
    index_view=CustomAdminIndexView(),
    base_template='admin/layout_admin.html'
)

