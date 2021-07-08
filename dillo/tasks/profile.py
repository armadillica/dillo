import logging
import typing

import requests
from allauth.account.models import EmailAddress
from background_task import background
from django.conf import settings
from micawber.contrib.mcdjango import providers

import dillo.models.profiles
from dillo.tasks.storage import download_image_from_web

log = logging.getLogger(__name__)


@background()
def update_profile_reel_thumbnail(user_id):

    profile = dillo.models.profiles.Profile.objects.get(user_id=user_id)
    oembed_data = providers.request(profile.reel)
    if 'thumbnail_url' not in oembed_data:
        return
    url = oembed_data['thumbnail_url']
    log.debug("Update profile for user %i" % user_id)
    download_image_from_web(url, profile.reel_thumbnail_16_9)


@background()
def update_mailing_list_subscription(user_email: str, is_subscribed: typing.Optional[bool] = None):
    """Subscribe or unsubscribe from newsletter.

    TODO(fsiddi) in the future we can accept an additional argument
    called `newsletter` to specify by name which newsletter to
    unsubscribe from.
    """

    if not hasattr(settings, 'ANYMAIL'):
        log.info("Mailgun not configured, skipping mailing list subscription update")
        return

    if not hasattr(settings, 'MAILING_LIST_NEWSLETTER_EMAIL'):
        log.debug("Newsletter not configured, skipping mailing list subscription update")
        return

    if not EmailAddress.objects.filter(verified=True, email=user_email).exists():
        log.info("No verified email address found, skipping mailing list update")
        return

    user = EmailAddress.objects.get(verified=True, email=user_email).user
    if not is_subscribed:
        is_subscribed = user.email_notifications_settings.is_enabled_for_newsletter

    api_url_base = f"https://api.mailgun.net/v3"
    api_url_newsletter = f"{api_url_base}/lists/{settings.MAILING_LIST_NEWSLETTER_EMAIL}"
    # Look for member in the mailing list.
    r_update = requests.put(
        f"{api_url_newsletter}/members/{user_email}",
        auth=('api', settings.ANYMAIL['MAILGUN_API_KEY']),
        data={
            'subscribed': str(is_subscribed).lower(),
            'name': user.profile.name,
            'vars': '{"first_name_guess": "' + user.profile.first_name_guess + '"}',
        },
    )
    # If a member was found, we are done.
    if r_update.status_code == 200:
        subscription_status = 'subscribed' if is_subscribed else 'unsubscribed'
        log.info(
            "Updated newsletter subscription status to '%s' for user %s"
            % (subscription_status, user_email)
        )
        return
    # If a member was not found and we want it subscribed.
    elif r_update.status_code == 404 and is_subscribed:
        r_create = requests.post(
            f"{api_url_newsletter}/members",
            auth=('api', settings.ANYMAIL['MAILGUN_API_KEY']),
            data={
                'address': user_email,
                'subscribed': str(is_subscribed).lower(),
                'name': user.profile.name,
                'vars': '{"first_name_guess": "' + user.profile.first_name_guess + '"}',
            },
        )
        if r_create.status_code != 200:
            log.error("Failed creating newsletter user for user %s" % user_email)
        else:
            log.info("Created newsletter user for %s" % user_email)
    elif r_update.status_code not in {200, 404}:
        log.error("Newsletter API returned status code %i" % r_update.status_code)


if settings.BACKGROUND_TASKS_AS_FOREGROUND:
    # Will execute activity_fanout_to_feeds immediately
    log.debug('Executing background tasks synchronously')
    update_profile_reel_thumbnail = update_profile_reel_thumbnail.task_function
    update_mailing_list_subscription = update_mailing_list_subscription.task_function
