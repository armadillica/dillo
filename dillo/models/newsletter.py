import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from dillo.models.mixins import CreatedUpdatedMixin

log = logging.getLogger(__name__)


class Newsletter(CreatedUpdatedMixin, models.Model):
    subject = models.CharField(max_length=150)
    body_txt = models.TextField()
    body_html = models.TextField()

    @property
    def body_html_and_unsubscribe(self):
        return render_to_string(
            f'dillo/emails/newsletter.pug',
            {'body_html': self.body_html, 'unsubscribe_url': '%mailing_list_unsubscribe_url%'},
        )

    @property
    def body_txt_and_unsubscribe(self):
        return f'{self.body_txt}\n\nUnsunscribe here: %mailing_list_unsubscribe_url%'

    def __str__(self):
        return self.subject + " - " + self.created_at.strftime("%B %d, %Y")

    def send(self):
        """Send the newsletter via Mailgun mailing list."""
        log.debug("Appending unsubscribe links")

        log.debug("Sending the newsletter to %s" % settings.MAILING_LIST_NEWSLETTER_EMAIL)
        send_mail(
            self.subject,
            self.body_txt_and_unsubscribe,
            settings.DEFAULT_FROM_EMAIL,
            [settings.MAILING_LIST_NEWSLETTER_EMAIL],
            fail_silently=False,
            html_message=self.body_html_and_unsubscribe,
        )

    def send_preview(self):
        """Send a preview copy of the newsletter to the admins."""
        subject = f"[Animato Newsletter Preview] {self.subject}"
        superusers_emails = User.objects.filter(is_superuser=True).values_list('email')
        superusers_emails_list = [email[0] for email in superusers_emails]
        send_mail(
            subject,
            self.body_txt_and_unsubscribe,
            settings.DEFAULT_FROM_EMAIL,
            superusers_emails_list,
            fail_silently=False,
            html_message=self.body_html_and_unsubscribe,
        )
