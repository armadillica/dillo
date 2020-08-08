from django.contrib import admin
from django.urls import include, path

import dillo.urls

# We need these URL patterns because we are developing a Django app. However,
# to be able to test our app we need an actual Django project. Here we define
# the URLs we use in our test project.
urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('admin/', admin.site.urls),
    path('', include(dillo.urls)),
]
