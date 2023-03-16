from django.conf import settings

from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """Whether to allow signups."""
        allow_signups = super(CustomAccountAdapter, self).is_open_for_signup(request)
        # Override with setting, otherwise default to super.
        return getattr(settings, 'ACCOUNT_ALLOW_SIGNUPS', allow_signups)
