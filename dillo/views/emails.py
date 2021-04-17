import hashlib
import json
import logging
import hmac
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.urls import reverse

from dillo.models.profiles import EmailNotificationsSettings

log = logging.getLogger(__name__)


class LikeContext:
    def __init__(
        self,
        subject: str,
        own_name: str,
        content_type: str,
        action_author_name: str,
        action_author_absolute_url: str,
        content_name: str,
        content_absolute_url: str,
    ):
        self.as_dict: dict = {
            'subject': subject,
            'content_type': content_type,
            'own_name': own_name,
            'action_author_name': action_author_name,
            'action_author_absolute_url': action_author_absolute_url,
            'content_name': content_name,
            'content_absolute_url': content_absolute_url,
        }


class FollowContext:
    def __init__(
        self,
        subject: str,
        own_name: str,
        own_profile_absolute_url: str,
        action_author_name: str,
        action_author_absolute_url: str,
    ):
        self.as_dict: dict = {
            'subject': subject,
            'own_name': own_name,
            'own_profile_absolute_url': own_profile_absolute_url,
            'action_author_name': action_author_name,
            'action_author_absolute_url': action_author_absolute_url,
        }


class CommentOrReplyContext:
    def __init__(
        self,
        subject: str,
        own_name: str,
        own_profile_absolute_url: str,
        action_author_name: str,
        action_author_absolute_url: str,
        content_name: str,
        content_absolute_url: str,
        content_text: str,
    ):
        self.as_dict: dict = {
            'subject': subject,
            'own_name': own_name,
            'own_profile_absolute_url': own_profile_absolute_url,
            'action_author_name': action_author_name,
            'action_author_absolute_url': action_author_absolute_url,
            'content_name': content_name,
            'content_absolute_url': content_absolute_url,
            'content_text': content_text,
        }


email_templates = {
    'like': LikeContext(
        subject='They love your work!',
        content_type='post',
        own_name='Koro',
        action_author_name='Harry',
        action_author_absolute_url='https://animato.local:8099/harry',
        content_name='My first post',
        content_absolute_url='https://animato.local:8099/',
    ).as_dict,
    'follow': FollowContext(
        subject='You are popular!',
        own_name='Koro',
        own_profile_absolute_url='https://animato.local:8099/koro',
        action_author_name='Harry',
        action_author_absolute_url='https://animato.local:8099/harry',
    ).as_dict,
    'comment': CommentOrReplyContext(
        subject='New comment on your post!',
        own_name='Koro',
        own_profile_absolute_url='https://animato.local:8099/koro',
        action_author_name='Harry',
        action_author_absolute_url='https://animato.local:8099/harry',
        content_name='My first post',
        content_absolute_url='http://animato.local:8099/p/kXnKeGJ#comments-1',
        content_text='I love your stuff!',
    ).as_dict,
    'reply': CommentOrReplyContext(
        subject='New comment on your post!',
        own_name='Koro',
        own_profile_absolute_url='https://animato.local:8099/koro',
        action_author_name='Harry',
        action_author_absolute_url='https://animato.local:8099/harry',
        content_name='My first post',
        content_absolute_url='http://animato.local:8099/p/kXnKeGJ#comments-1',
        content_text='I love your stuff!',
    ).as_dict,
}


def preview_email_list(request):
    """Display a list of the supported email templates."""
    return render(request, 'dillo/emails/preview_list.pug', {'email_templates': email_templates})


def preview_email_detail(request, email_template):
    """Display a single email template, with some mock data."""
    if email_template not in email_templates:
        log.debug('Template %s does not exist' % email_template)
        raise Http404("A template for this email template does not exist")

    return render(request, f'dillo/emails/{email_template}.pug', email_templates[email_template])


@login_required
def preview_email_send(request, email_template):
    from dillo.tasks.emails import send_notification_mail

    log.debug("Sending '%s' mail message to %s" % (email_template, request.user.email))
    send_notification_mail(
        subject=f'Test email for {email_template}',
        recipient=request.user,
        template=email_template,
        context=email_templates[email_template],
    )
    message = f'Mail preview for {email_template} sent to {request.user.email}'
    messages.add_message(request, messages.INFO, message)
    log.debug(message)
    return redirect(reverse('preview_email_template_list'))


@csrf_exempt
@require_POST
def webhook_newlsetter_unsubscribe(request):
    """Handle unsubscribe notifications from mailing-lists."""

    def verify(token, timestamp, signature):
        hmac_digest = hmac.new(
            key=settings.ANYMAIL['MAILGUN_API_KEY'].encode(),
            msg=f'{timestamp}{token}'.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(str(signature), str(hmac_digest))

    r_json = json.loads(request.body)
    doc_signature = r_json['signature']
    if not verify(doc_signature['token'], doc_signature['timestamp'], doc_signature['signature']):
        log.error("Failed to verify request from Mailgun")
        return HttpResponseBadRequest()
    # Process the webhook
    doc_event_data = r_json['event-data']
    event = doc_event_data['event']
    if event == 'unsubscribed':
        try:
            user = User.objects.get(email=doc_event_data['recipient'])
        except User.DoesNotExist:
            log.error("User not found for email %s" % doc_event_data['recipient'])
            return HttpResponse('OK')
        log.info("Unsubscribing user %i from newsletter" % user.id)
        EmailNotificationsSettings.objects.filter(user=user).update(is_enabled_for_newsletter=False)
        return HttpResponse('OK')
    return HttpResponseBadRequest()
