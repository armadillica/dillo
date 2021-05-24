from django.urls import path

import dillo.views.users.homepage

urlpatterns = [
    path('', dillo.views.users.homepage.HomepageRouter.as_view(), name='homepage'),
]
