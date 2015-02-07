from application import db
from application.modules.users.model import User
from application.modules.admin import CustomModelView, backend

# -------- Views --------
class UserView(CustomModelView):
    column_list = ('email', 'active', 'first_name', 'last_name')
    column_filters = ('id', 'email', 'active', 'first_name', 'last_name')


# Add views
backend.add_view(UserView(User, db.session, name='Users', url='users'))