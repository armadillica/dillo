import logging

from django.conf import settings
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
        return f"{self.subject} - {self.created_at.strftime('%B %d, %Y')}"

    def send(self, is_preview=True):
        """Send the newsletter via Mailgun mailing list.

        If is_preview is true, we send to a testing mailing list (same
        config as a production list, just with a limited number of
        subscribers).
        """
        log.debug("Appending unsubscribe links")

        mailig_list_address = settings.MAILING_LIST_NEWSLETTER_EMAIL
        if is_preview:
            mailig_list_address = settings.MAILING_LIST_NEWSLETTER_EMAIL_PREVIEW

        log.debug("Sending the newsletter to %s" % mailig_list_address)
        send_mail(
            self.subject,
            self.body_txt_and_unsubscribe,
            settings.DEFAULT_FROM_EMAIL,
            [mailig_list_address],
            fail_silently=False,
            html_message=self.body_html_and_unsubscribe,
        )
