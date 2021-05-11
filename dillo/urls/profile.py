from django.urls import path

import dillo.views.users.profile

urlpatterns = [
    path(
        '<username>/', dillo.views.users.profile.ProfileDetailView.as_view(), name='profile-detail'
    )
]
