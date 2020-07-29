import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.views.generic import TemplateView, FormView
from django.views.generic.edit import UpdateView


import dillo.forms
from dillo import forms
from dillo.models.profiles import EmailNotificationsSettings

log = logging.getLogger(__name__)


class AccountSettings(LoginRequiredMixin, TemplateView):
    """Interface to perform dangerous operations.

    For example:
    - change account username
    - delete account
    """

    template_name = 'dillo/account_settings.pug'


class AccountDelete(LoginRequiredMixin, FormView):
    template_name = 'dillo/generic_form_embed.pug'
    form_class = forms.DeactivateUserForm

    def form_valid(self, form):
        log.debug('Fetching user %i for deletion' % self.request.user.id)
        user = User.objects.get(pk=self.request.user.id)
        user.delete()
        return super(AccountDelete, self).form_valid(form)

    def get_context_data(self, **kwargs):
        """Insert action_url into the context dict."""
        context = super().get_context_data(**kwargs)
        context['action_url'] = reverse('account_delete')
        context['submit_label'] = "Yes, Delete Account"
        context['submit_class'] = "btn-danger"
        return context

    def get_success_url(self):
        return reverse('account_delete_success')


class AccountUpdateUsername(LoginRequiredMixin, FormView):
    """Display a simple form to allow username change."""

    template_name = 'dillo/generic_form_embed.pug'
    form_class = forms.AccountUpdateUsernameForm

    def get_initial(self):
        initial = super(AccountUpdateUsername, self).get_initial()
        initial.update({'username': self.request.user.username})
        return initial

    def form_valid(self, form):
        log.debug('Updating username for user %i' % self.request.user.id)
        self.request.user.username = form.cleaned_data['username']
        self.request.user.save()
        return super(AccountUpdateUsername, self).form_valid(form)

    def get_context_data(self, **kwargs):
        """Insert action_url into the context dict."""
        context = super().get_context_data(**kwargs)
        context['action_url'] = reverse('account_update_username')
        context['submit_label'] = "Update username"
        context['submit_class'] = "btn-danger"
        return context

    def get_success_url(self):
        return reverse('account_update_username_success')


class AccountEmailNotificationsView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    template_name = 'dillo/account_notifications.pug'
    model = EmailNotificationsSettings
    fields = [
        'is_enabled',
        'is_enabled_for_like',
        'is_enabled_for_follow',
        'is_enabled_for_comment',
        'is_enabled_for_reply',
        'is_enabled_for_newsletter',
    ]
    success_message = "Email notifications updated successfully"

    def get_object(self, queryset=None):
        return EmailNotificationsSettings.objects.get(user=self.request.user)

    def get_success_url(self):
        return reverse('account-email-notifications')
