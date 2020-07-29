from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


class CustomLogoutView(LogoutView):
    """Custom logout view.

    Allows returning back to super user if we used loginas, and does
    not require the /admin/ endpoint, which is required by the default
    implementation of loginas.
    """

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        from loginas.utils import restore_original_login

        restore_original_login(request)
        return redirect('/')
