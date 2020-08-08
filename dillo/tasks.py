import logging
import pathlib
import typing
import requests
from urllib.parse import urlparse

from allauth.account.models import EmailAddress
from actstream import models as models_actstream
from background_task import background
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mass_mail, send_mail, EmailMessage

from django.template.defaultfilters import truncatechars
from django.template.loader import render_to_string
from django.urls import reverse
from micawber.contrib.mcdjango import providers
from taggit import models as models_taggit

import dillo.coconut.job
import dillo.models
import dillo.models.feeds
import dillo.models.messages
import dillo.models.posts
import dillo.models.profiles
import dillo.models.mixins
import dillo.views.emails

log = logging.getLogger(__name__)


@background()
def create_job(post_hash_id: str, video_id: int, source_path: str):
    """Create video encoding jobs.

    Because of the @background decorator, we only accept hashable
    arguments.

    The video versions produced are the following:
    - a regular 720p, h264 with mp4 container
    - an httpstream using fragmented mp4, compatible with DASH and HLS
      with two variants (these are WIP and should be tweaked):
      - mp4:480p_1500k
      - mp4:720p
    """
    if not settings.COCONUT_API_KEY:
        log.info('Missing COCONUT_API_KEY: no video encoding will be performed')
        return

    # The base SFTP path, with credentials
    job_storage_base = settings.COCONUT_SFTP_STORAGE
    job_storage_base_out = job_storage_base

    # Override settings if debug mode
    if settings.DEBUG:
        job_storage_base = f'{settings.COCONUT_DECLARED_HOSTNAME}/media/'
        job_storage_base_out = f'{settings.COCONUT_DECLARED_HOSTNAME}/debug-video-transfer/'

    # Outputs
    outputs = {}

    source_path = pathlib.PurePath(source_path)

    # The jpg:1280x thumbnail
    outputs['jpg:1280x'] = f"{job_storage_base_out}{source_path.with_suffix('.thumbnail.jpg')}"

    # The gif:240x preview
    outputs['gif:240x'] = f"{job_storage_base_out}{source_path.with_suffix('.preview.gif')}"

    # The mp4:720p version of the path (relative to MEDIA_ROOT)
    outputs['mp4:0x720'] = f"{job_storage_base_out}{source_path.with_suffix('.720p.mp4')}"

    # The httpstream packaging configuration
    httpstream_packaging = 'dash+hlsfmp4=/stream'

    # The httpstream variants
    httpstream_variants = 'variants=mp4:480p_1500k,mp4:720p'

    # TODO(fsiddi) enable support for httpstream
    # outputs['httpstream'] = f'{job_storage_base_out}{source_path.parent}, ' \
    #     f'{httpstream_packaging}, {httpstream_variants}'

    # Webhook for encoding updates
    job_webhook = reverse(
        'post_update_video_processing', kwargs={'hash_id': post_hash_id, 'video_id': video_id}
    )

    j = dillo.coconut.job.create(
        api_key=settings.COCONUT_API_KEY,
        source=f'{job_storage_base}{source_path}',
        webhook=f'{settings.COCONUT_DECLARED_HOSTNAME}{job_webhook}, events=true, metadata=true',
        outputs=outputs,
    )

    if j['status'] == 'ok':
        log.info('Started processing job %i' % j['id'])
    else:
        log.error('Error %s - %s' % (j['error_code'], j['message']))


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


def feeds_fanout_liked(action):
    # Do not notify user of own activity
    content_type = ContentType.objects.get_for_model(action.action_object)
    if content_type.name not in {'post', 'comment'}:
        log.error('Attempting to fanout a %s' % content_type)
        return

    recipient: User = action.action_object.user
    if action.actor == recipient:
        return
    # Fanout like notifications (only to owner)
    log.debug('Update notification feed about like')
    dillo.models.feeds.FeedEntry.objects.create(
        user=recipient, action=action,
    )
    # Email notifications
    log.debug('Sending notification email to user %i', recipient.id)

    if content_type.name == 'post':
        content_name = action.action_object.title
    else:  # The only other possible case is 'comment'
        content_name = action.action_object.content

    # Prepare attributes
    content_name = truncatechars(content_name, 15)
    like_context = dillo.views.emails.LikeContext(
        subject=f'They love your {content_type.name}!',
        content_type=content_type.name,
        own_name=recipient.profile.first_name_guess or recipient.username,
        action_author_name=action.actor.profile.first_name_guess or action.actor.username,
        action_author_absolute_url=action.actor.profile.absolute_url,
        content_name=content_name,
        content_absolute_url=action.action_object.absolute_url,
    ).as_dict

    send_notification_mail(
        f'Your {content_type.name} has a new like!',
        recipient,
        template='like',
        context=like_context,
    )


def feeds_fanout_commented(action):
    # Fan out notification to Post followers
    for follower in models_actstream.followers(action.action_object.post):
        if action.actor == follower:
            log.debug('Skipping notification generation post owner')
            continue
        log.debug(
            'Generating notification for user %i about comment %i'
            % (follower.id, action.action_object.id)
        )
        follower.feed_entries.create(action=action)
        # Email notification
        content_name = truncatechars(action.action_object.post.title, 15)
        content_text = truncatechars(action.action_object.content, 25)
        comment_context = dillo.views.emails.CommentOrReplyContext(
            subject='Your post has a new comment!',
            own_name=follower.profile.first_name_guess or follower.username,
            own_profile_absolute_url=follower.profile.absolute_url,
            action_author_name=action.actor.profile.first_name_guess or action.actor.username,
            action_author_absolute_url=action.actor.profile.absolute_url,
            content_name=content_name,
            content_absolute_url=f'{action.action_object.post.absolute_url}#comments-'
            f'{action.action_object.id}',
            content_text=content_text,
        ).as_dict

        send_notification_mail(
            f'Your post "{content_name}" has a new comment',
            follower,
            template='comment',
            context=comment_context,
        )


def feeds_fanout_replied(action):
    """Distribute notifications about a comment being replied to."""
    # Fan out notification to parent Comment followers
    for follower in models_actstream.followers(action.action_object.parent_comment):
        if action.actor == follower:
            # If the reply author is the same as the parent comment author
            log.debug('Skipping notification generation for comment owner')
            continue
        log.debug(
            'Generating notification for user %i about reply %i'
            % (follower.id, action.action_object.id)
        )
        follower.feed_entries.create(action=action)
        # Email notification
        content_name = truncatechars(action.action_object.post.title, 15)
        content_text = truncatechars(action.action_object.content, 25)
        reply_context = dillo.views.emails.CommentOrReplyContext(
            subject='Your comment has a new reply!',
            own_name=follower.profile.first_name_guess or follower.username,
            own_profile_absolute_url=follower.profile.absolute_url,
            action_author_name=action.actor.profile.first_name_guess or action.actor.username,
            action_author_absolute_url=action.actor.profile.absolute_url,
            content_name=content_name,
            content_absolute_url=f'{action.action_object.post.absolute_url}#comments-'
            f'{action.action_object.id}',
            content_text=content_text,
        ).as_dict
        send_notification_mail(
            f'Your comment has a new reply!', follower, template='reply', context=reply_context,
        )


def feeds_fanout_started_following(action):
    originally_target_content_type = ContentType.objects.get_for_model(action.target)
    originally_target = action.target

    # This addresses an issue in the actstream package. The 'started following'
    # activities uses the incorrect semantics <actor> <verb> <target> instead of
    # <actor> <verb> <object>. In order to fix this, and have notifications to
    # read correctly, we update the action object by moving the target to the
    # action_object property. We use the update method so we don't trigger a
    # new notification.

    log.debug('Moving misplaced target into action_object')
    models_actstream.Action.objects.filter(pk=action.id).update(
        target_object_id=None,
        target_content_type_id=None,
        action_object_object_id=originally_target.id,
        action_object_content_type_id=originally_target_content_type.id,
    )

    # If user followed another user, notify the followed user
    # Notifications will only be generated from User-related activities
    if originally_target_content_type.model_class() != User:
        return

    # Count existing activities with the same actor and object
    actions_count = models_actstream.Action.objects.filter(
        action_object_object_id=originally_target.id,
        action_object_content_type_id=originally_target_content_type.id,
        actor_object_id=action.actor.id,
        actor_content_type_id=ContentType.objects.get_for_model(action.actor).id,
    ).count()

    # If the action already exists (i.e. user followed, then unfollowed a user)
    # do not generate another notification
    if actions_count > 1:
        log.debug('Skipping generation of follow notification, it exists already')
        return

    # Create notification
    log.debug('Generating follow notification for user %i' % action.target.id)
    action.target.feed_entries.create(action=action)

    # Email notification
    follow_context = dillo.views.emails.FollowContext(
        subject='You have a new follower!',
        own_name=action.target.profile.first_name_guess or action.target.username,
        own_profile_absolute_url=action.target.profile.absolute_url,
        action_author_name=action.actor.profile.first_name_guess or action.actor.username,
        action_author_absolute_url=action.actor.profile.absolute_url,
    ).as_dict
    send_notification_mail(
        f'You have a new follower!', action.target, template='follow', context=follow_context,
    )


def feeds_fanout_posted(action):
    """Populate users feeds from the given action."""
    # Define list of processed users (to prevent multiple timeline
    # entries for the same post)
    processed_users = []

    def add_to_timeline(user, action):
        user.feed_entries.create(
            category='timeline', action=action,
        )
        log.debug('Adding post activity %i to user %i timeline' % (action.id, user.id))
        processed_users.append(user)

    # Add to the timeline of the post owner
    add_to_timeline(action.actor, action)

    # Find followers of user
    for follower in models_actstream.followers(action.actor):
        add_to_timeline(follower, action)

    for tag in action.action_object.tags.all():
        for follower in models_actstream.followers(tag):
            if follower in processed_users:
                log.debug('Skip adding post to timeline, it exists already')
                continue
            add_to_timeline(follower, action)


fanout_functions = {
    'liked': feeds_fanout_liked,
    'commented': feeds_fanout_commented,
    'replied': feeds_fanout_replied,
    'started following': feeds_fanout_started_following,
    'posted': feeds_fanout_posted,
}


@background()
def activity_fanout_to_feeds(actstream_action_id):
    action = models_actstream.Action.objects.get(pk=actstream_action_id)
    log.debug('Processing "%s" action for feed fanout' % action.verb)
    fanout_functions[action.verb](action)


@background()
def repopulate_timeline_content(content_type: ContentType, object_id, user_id, action):
    """Based on the follow/unfollow action.

    Only repopulates if a User object is being followed or unfollowed.
    Tags are TODO.
    """

    def push_action_in_user_feed(user, action):
        # Push activities if they don't exist
        if user.feed_entries.filter(action_id=action.pk).exists():
            log.debug('Skipping existing activity in user feed')
            return
        else:
            log.debug('Populating timeline with action %i' % action.pk)
            user.feed_entries.create(
                category='timeline', action=action,
            )

    def pull_action_from_user_feed(user, action):
        # Do a lookup on the current user's feed, and remove any matching activity found.
        try:
            log.debug('Removing action %i from user %i feed' % (action.pk, user.pk))
            user.feed_entries.filter(action_id=action.pk).delete()
        except dillo.models.feeds.FeedEntry.DoesNotExist:
            pass

    content_type_class = content_type.model_class()
    try:
        target = content_type.get_object_for_this_type(pk=object_id)
    except content_type_class.DoesNotExist:
        log.debug("Skipping timeline repopulation, content was deleted")
        return
    # If follow User
    if action == 'follow' and isinstance(target, User):
        # If following user, get 10 posts and check if their creation activity is already in the
        # users timeline feed. If not, add push to the timeline
        actions = models_actstream.Action.objects.filter(verb='posted', actor_object_id=target.pk)[
            :10
        ]
        user = User.objects.get(pk=user_id)
        for action in actions:
            push_action_in_user_feed(user, action)
    elif action == 'follow' and isinstance(target, models_taggit.Tag):
        # Get 10 posts with that tag
        posts = dillo.models.posts.Post.objects.filter(tags__name__in=[target.name])[:10]
        for post in posts:
            # Find post action
            action = models_actstream.Action.objects.get(
                verb='posted', action_object_object_id=post.pk
            )
            push_action_in_user_feed(User.objects.get(pk=user_id), action)
    # If unfollow User
    elif action == 'unfollow' and isinstance(target, User):
        # Fetch all actions from the unfollowed users
        actions = models_actstream.Action.objects.filter(
            verb='posted', actor_object_id=target.pk
        ).all()
        # Fetch current user
        user = User.objects.get(pk=user_id)
        for action in actions:
            pull_action_from_user_feed(user, action)
    elif action == 'unfollow' and isinstance(target, models_taggit.Tag):
        # Get the latest 10 posts with that tag
        posts = dillo.models.posts.Post.objects.filter(tags__name__in=[target.name]).order_by(
            '-created_at'
        )[:10]
        for post in posts:
            # Find post action
            action = models_actstream.Action.objects.get(
                verb='posted', action_object_object_id=post.pk
            )
            user = User.objects.get(pk=user_id)
            pull_action_from_user_feed(user, action)


def download_image_from_web(url, model_instance):
    # Build request (streaming)
    r = requests.get(url, stream=True)
    # Get the path component from the url
    path_comp = urlparse(url)[2]
    hashed_path = dillo.models.mixins.get_upload_to_hashed_path(model_instance, path_comp)
    src = pathlib.Path(settings.MEDIA_ROOT, hashed_path)
    src.parent.mkdir(parents=True, exist_ok=True)

    # Download the file
    with src.open('wb') as fp:
        log.debug("Downloading file %s to %s" % (url, str(src)))
        for chunk in r.iter_content(chunk_size=128):
            fp.write(chunk)
    return hashed_path


@background()
def update_profile_reel_thumbnail(user_id):

    profile = dillo.models.profiles.Profile.objects.get(user_id=user_id)
    oembed_data = providers.request(profile.reel)
    if 'thumbnail_url' not in oembed_data:
        return
    url = oembed_data['thumbnail_url']
    hashed_path = download_image_from_web(url, dillo.models.posts.PostMediaImage())
    log.debug("Update profile for user %i" % user_id)
    dillo.models.profiles.Profile.objects.filter(user_id=user_id).update(
        reel_thumbnail_16_9=hashed_path
    )

    # TODO(fsiddi) empty sorl cache


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
    log.debug('Executing background tasks syncronously')
    activity_fanout_to_feeds = activity_fanout_to_feeds.task_function
    send_mail_report_content = send_mail_report_content.task_function
    repopulate_timeline_content = repopulate_timeline_content.task_function
    send_mail_message_contact = send_mail_message_contact.task_function
    update_profile_reel_thumbnail = update_profile_reel_thumbnail.task_function
    update_mailing_list_subscription = update_mailing_list_subscription.task_function
