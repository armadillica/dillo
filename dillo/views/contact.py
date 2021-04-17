import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import FormView

import dillo.tasks.emails
from dillo import forms, tasks
from dillo.models.messages import MessageContact

log = logging.getLogger(__name__)


class ContactView(LoginRequiredMixin, FormView):
    """Form view for content reporting. Loaded embedded in a modal."""

    template_name = 'dillo/generic_form_embed.pug'
    form_class = forms.ContactForm

    def get_success_url(self):
        return reverse('contact-success')

    def form_valid(self, form):
        """Generate a Contact Message and schedule an email notification."""
        log.info("Creating contact message from user %i" % self.request.user.pk)
        message = MessageContact.objects.create(
            user=self.request.user, message=form.cleaned_data['message'],
        )
        dillo.tasks.emails.send_mail_message_contact(message.id)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Insert the form and url construction data into the context dict."""
        context = super().get_context_data(**kwargs)
        context['action_url'] = reverse('contact')
        context['submit_label'] = "Send Message"
        return context
