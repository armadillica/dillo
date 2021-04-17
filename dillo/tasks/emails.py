import logging
from background_task import background
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mass_mail, EmailMessage, send_mail
from django.template.loader import render_to_string

import dillo.models.messages
import dillo.models.posts
import dillo.views

log = logging.getLogger(__name__)


@background()
def send_mail_report_content(report_id: int):
    """Given a report_id, send an email to all superusers."""
    log.info("Sending email notification for report %i" % report_id)
    superusers_emails = User.objects.filter(is_superuser=True).values_list('email')
    report = dillo.models.messages.ContentReports.objects.get(pk=report_id)

    # Display report info. The "Content" line has content if the content is a
    # Post or a Comment with a .content or .title attribute.

    if isinstance(report.content_object, dillo.models.posts.Post):
        content = report.content_object.title
    else:
        content = report.content_object.content

    content_body = (
        f"User: {report.user} \n"
        f"Content URL: {report.content_object.absolute_url} \n"
        f"Content: {content} \n"
        f"Reason: {report.reason} \n"
    )

    if report.notes:
        content_body += f"\n Notes: {report.notes}"

    messages = (
        ('Report for content', content_body, settings.DEFAULT_FROM_EMAIL, email)
        for email in superusers_emails
    )
    send_mass_mail(messages)


@background()
def send_mail_message_contact(message_id: int):
    """Given a message_id, send an email to all superusers."""
    log.info("Sending email notification for message %i" % message_id)
    superusers = User.objects.filter(is_superuser=True).all()
    message = dillo.models.messages.MessageContact.objects.get(pk=message_id)

    subject = f"Message from {message.user}"
    body = message.message

    email = EmailMessage(
        subject,
        body,
        from_email=message.user.email,
        to=[superuser.email for superuser in superusers],
        reply_to=[message.user.email],
    )
    email.send()


def send_notification_mail(subject: str, recipient: User, template, context: dict):
    """Generic email notification function.

    Args:
        subject (str): The mail subject
        recipient (User): The recipient
        template (str): The template to be used
        context (dict): Template variables, differ depending on the template used

    Features simple text (not even HTML message yet).
    """

    if settings.EMAIL_BACKEND == 'anymail.backends.mailgun.EmailBackend':
        if not hasattr(settings, 'ANYMAIL') or not settings.ANYMAIL['MAILGUN_API_KEY']:
            log.info("Skipping email notification, mail not configured")
            return

    # Ensure use of a valid template
    if template not in dillo.views.emails.email_templates:
        log.error("Email template '%s' not found" % template)
        return
    # Send mail only if recipient allowed it in the settings
    if not recipient.email_notifications_settings.is_enabled:
        log.debug('Skipping email notification for user %i' % recipient.id)
        return

    message_type_specific_setting = f'is_enabled_for_{template}'
    if not getattr(recipient.email_notifications_settings, message_type_specific_setting):
        log.debug('Skipping %s email notification for user %i' % (template, recipient.id))
        return

    # Ensure that the context dict contains all the expected values
    for k, _ in dillo.views.emails.email_templates[template].items():
        if k not in context:
            log.error("Missing context variable %s" % k)

    log.debug('Sending email notification to user %i' % recipient.id)

    # plaintext_context = Context(autoescape=False)  # HTML escaping not appropriate in plaintext
    text_body = render_to_string(f'dillo/emails/{template}.txt', context)
    html_body = render_to_string(f'dillo/emails/{template}.pug', context)

    send_mail(
        subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        [recipient.email],
        fail_silently=False,
        html_message=html_body,
    )


if settings.BACKGROUND_TASKS_AS_FOREGROUND:
    # Will execute activity_fanout_to_feeds immediately
    log.debug('Executing background tasks synchronously')
    send_mail_report_content = send_mail_report_content.task_function
    send_mail_message_contact = send_mail_message_contact.task_function
