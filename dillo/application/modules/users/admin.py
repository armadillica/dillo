from flask import redirect, url_for
from flask.ext.admin import expose
from flask.ext.admin.model.template import macro
from flask.ext.login import login_user
from application import db
from application.modules.users.model import User
from application.modules.users.model import user_datastore
from application.modules.admin import CustomModelView, CustomBaseView, backend


class UserOperationsView(CustomBaseView):
    @expose('/')
    def index(self):
        return redirect(url_for('index'))

    @expose('/login/<int:user_id>/')
    def login(self, user_id):
        user = user_datastore.get_user(user_id)
        login_user(user)
        return redirect(url_for('index'))


class UserView(CustomModelView):
    column_list = ('email', 'active', 'username', 'first_name', 'last_name',
                   'user_operations')
    column_filters = ('id', 'email', 'active', 'username', 'first_name',
                      'last_name')
    column_formatters = dict(user_operations=macro('user_operations'))
    list_template = 'admin/user/list.html'

# Add views
backend.add_view(UserView(User, db.session, name='Users', url='users'))
backend.add_view(UserOperationsView(name='User Operations',
                                    endpoint='user-operations',
                                    url='user-operations'))
