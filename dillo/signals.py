import logging
import typing
import re
import pathlib
import requests
import shutil

from actstream import action, models as models_actstream
from actstream.actions import follow
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db.models.signals import post_save, post_delete, pre_delete
from django.db.models import F
from django.db import IntegrityError, transaction
from django.dispatch import receiver
from allauth.account.signals import email_confirmed, email_changed

import dillo.models.mixins
import dillo.models.posts
import dillo.models.profiles
from dillo import tasks

log = logging.getLogger(__name__)

find_hashtags_re = re.compile(r'(?i)(?<=\#)\w+', re.UNICODE)
find_mentions_re = re.compile(r'\B@\w*[a-zA-Z]+\w*')


def extract_tags_and_mentions(s: str) -> typing.Tuple[set, set]:
    """Extract tags and mentions from a string.

    Returns a tuple with a set of tags and mentioned users, if they exist.
    """
    if not s:
        return set(), set()

    # Build a set after stripping the # or @ sign before every item found with
    # the regular expression.
    tags = set(t for t in find_hashtags_re.findall(s))
    mentions = set(m[1:] for m in find_mentions_re.findall(s))
    mentioned_user = set(
        User.objects.get(username=username)
        for username in mentions
        if User.objects.filter(username=username).exists()
    )

    # mentions = set(m for m in mentions)

    return tags, mentioned_user


@receiver(post_save, sender=User)
def create_profile_and_notifications_settings(sender, instance: User, created, **kwargs):
    from dillo.models.profiles import Profile
    from dillo.models.profiles import EmailNotificationsSettings

    if not created:
        return

    my_log = log.getChild('create_profile_and_notifications_settings')
    try:
        customer = instance.profile
    except Profile.DoesNotExist:
        pass
    else:
        my_log.debug(
            'Newly created User %d already has a Profile %d, not creating new one',
            instance.pk,
            customer.pk,
        )
        return

    my_log.info('Creating new Profile due to creation of user %s', instance.pk)
    Profile.objects.create(user=instance)
    my_log.info('Creating email notifications settings for user %s', instance.pk)
    EmailNotificationsSettings.objects.create(user=instance)


@receiver(post_save, sender=dillo.models.posts.Post)
def on_created_post(sender, instance: dillo.models.posts.Post, created, **kwargs):
    """On post creation, set hash_id."""
    if not created:
        return
    instance.hash_id = instance.id
    instance.save()
    log.debug('Set user %s as follower of own post %i' % (instance.user, instance.id))
    follow(instance.user, instance, actor_only=False)


@receiver(post_save, sender=dillo.models.posts.Post)
def on_saved_post(sender, instance: dillo.models.posts.Post, created, **kwargs):
    """Assign Tags and Mentions to a Post by parsing the description."""
    # If the post was just created, stop here since we have no tags yet
    if created:
        return
    # Extract tags and mentions from text and assign them to the Post
    tags, mentions = extract_tags_and_mentions(instance.title)
    instance.tags.set(*tags)
    # Delete all existing mentions
    dillo.models.mixins.Mentions.objects.filter(
        content_type_id=instance.content_type_id, object_id=instance.id
    ).delete()
    for mentioned_user in mentions:
        log.debug('Mentioning user %s in Post %i' % (mentioned_user, instance.id))
        dillo.models.mixins.Mentions.objects.create(
            user=mentioned_user, content_object=instance,
        )


@receiver(dillo.models.posts.post_published, sender=dillo.models.posts.Post)
def on_post_published(sender, instance: dillo.models.posts.Post, **kwargs):
    """Create activity for publised Post."""
    # If activity was already created (the post was already published),
    # skip this signal to prevent the activity from appearing twice in the feeds.
    if models_actstream.Action.objects.filter(
        actor_object_id=instance.user.id, action_object_object_id=instance.id, verb='posted'
    ).exists():
        log.info('Content already published, skipping notification generation')
        return
    action.send(instance.user, verb='posted', action_object=instance)


@receiver(post_save, sender=dillo.models.posts.Comment)
def on_created_comment(sender, instance: dillo.models.posts.Comment, created, **kwargs):
    """Assign tags to a comment by parsing the content."""
    if not created:
        return
    # Extract tags and mentions from text and assign them to the Comment
    tags, mentions = extract_tags_and_mentions(instance.content)
    instance.tags.set(*tags)
    for mentioned_user in mentions:
        log.debug('Mentioning user %s in Comment %i' % (mentioned_user, instance.id))
        dillo.models.mixins.Mentions.objects.create(
            user=mentioned_user, content_object=instance,
        )
        # TODO(fsiddi) Generate activity about mention

    # Generate activity about comment creation
    log.debug('Generating activity about comment creation')
    verb = 'commented'
    if instance.parent_comment:
        verb = 'replied'
    action.send(instance.user, verb=verb, action_object=instance, target=instance.post)
    log.debug('Set user %s as follower of own comment %i' % (instance.user, instance.id))
    follow(instance.user, instance, actor_only=False)


@receiver(post_delete, sender=dillo.models.posts.PostMedia)
def on_deleted_post_media_delete_content_object(sender, instance, using, **kwargs):
    """Delete referenced PostMediaImage or PostMediaVideo."""
    instance.content_object.delete()
    log.debug('Deleted media element for PostMedia %i' % instance.id)


@receiver(post_delete, sender=dillo.models.posts.PostMediaImage)
def on_deleted_post_media_image_remove_file(sender, instance, **kwargs):
    """Delete image file after PostMediaImage instance is deleted."""
    if not instance.image:
        return
    instance.image.delete(False)
    log.debug('Removed image from filesystem PostMedia %s' % instance.image)


@receiver(post_delete, sender=dillo.models.posts.PostMediaVideo)
def on_deleted_post_media_video_remove_files(sender, instance, **kwargs):
    """Delete image file after PostMediaImage instance is deleted."""
    if not instance.source:
        return
    parent_dir = pathlib.PurePath(instance.source.path).parent
    shutil.rmtree(parent_dir)
    log.debug('Removed %s from filesystem' % parent_dir)


@receiver(post_save, sender=dillo.models.mixins.Likes)
def on_created_like(sender, instance: dillo.models.mixins.Likes, created, **kwargs):
    """Actions to perform once a Like is created."""

    # Make the liked_object explicit
    if isinstance(instance.content_object, dillo.models.posts.Comment):
        liked_object = 'comment'
    elif isinstance(instance.content_object, dillo.models.posts.Post):
        liked_object = 'post'
    else:
        return

    if liked_object == 'comment' and instance.content_object.parent_comment:
        target = instance.content_object.parent_comment
    else:
        target = None

    log.debug('Generating like activity')
    # TODO(fsiddi) Prevent duplicate activity.
    # If the user likes a post or comment after having unliked it, do not generate activity.
    action.send(instance.user, verb='liked', action_object=instance.content_object, target=target)

    # Increase likes_count for profile of post owner when a Post is liked.
    if not created or liked_object != 'post':
        return
    target_user = instance.content_object.user
    dillo.models.profiles.Profile.objects.filter(user=target_user).update(
        likes_count=F('likes_count') + 1
    )
    log.debug('Increased like count for user %s' % target_user)


def profile_likes_count_decrease(target_user: User):
    """Decrease user profile likes of -1.

    The function is available as standalone for easier unit testing.
    """
    try:
        with transaction.atomic():
            dillo.models.profiles.Profile.objects.filter(user=target_user).update(
                likes_count=F('likes_count') - 1
            )
    except IntegrityError:
        log.warning('Integrity error when incrementing likes count for user %i' % target_user.id)
        target_user.profile.recalculate_likes()


@receiver(post_delete, sender=dillo.models.mixins.Likes)
def on_deleted_like(sender, instance: dillo.models.mixins.Likes, **kwargs):
    """Decrease likes_count for profile of post owner when a Post is unliked."""
    if not isinstance(instance.content_object, dillo.models.posts.Post):
        return
    target_user = instance.content_object.user
    profile_likes_count_decrease(target_user)
    log.debug('Decreased like count for user %s' % target_user)


@receiver(post_save, sender=SocialAccount)
def on_social_account_added(sender, instance: SocialAccount, created, **kwargs):
    """Fetch social account name and avatar, and add them to the Profile."""
    if not created:
        return
    name = instance.extra_data.get('name')
    if name:
        log.debug('Updating name via socialaccount for user %i' % instance.user.id)
        instance.user.profile.name = name
        instance.user.profile.save()

    # Look for Social Account avatar and update the avatar
    url_avatar = instance.get_avatar_url()
    if url_avatar:
        log.debug('Updating avatar via socialaccount for user %i' % instance.user.id)
        image_content = ContentFile(requests.get(url_avatar).content)
        instance.user.profile.avatar.save("profile.jpg", image_content)


@receiver(post_save, sender=models_actstream.Action)
def on_created_action(sender, instance: models_actstream.Action, created, **kwargs):
    """On action created, fan out notifications"""
    if not created:
        return
    log.debug('Creating background fanout operation for action %i' % instance.id)
    tasks.activity_fanout_to_feeds(instance.id)


@receiver(post_save, sender=models_actstream.Follow)
def on_created_follow(sender, instance: models_actstream.Follow, created, **kwargs):
    if not created:
        return
    content_type = ContentType.objects.get_for_id(instance.content_type_id)
    tasks.repopulate_timeline_content(content_type, instance.object_id, instance.user_id, 'follow')


@receiver(post_delete, sender=models_actstream.Follow)
def on_deleted_follow(sender, instance: models_actstream.Follow, **kwargs):
    """User stops following something."""
    content_type = ContentType.objects.get_for_id(instance.content_type_id)
    log.debug("Unfollowing %s %s" % (content_type.name, instance.object_id))
    tasks.repopulate_timeline_content(
        content_type, instance.object_id, instance.user_id, 'unfollow'
    )


@receiver(email_confirmed)
def on_email_confirmed(request, email_address, **kwargs):
    """If confirmed, subscribe to newsletter."""
    tasks.update_mailing_list_subscription(email_address, True)


@receiver(email_changed)
def on_email_email_changed(request, user, from_email_address, to_email_address, **kwargs):
    """Unsubscribe previous email, wait for new one to be confirmed."""
    if from_email_address:
        tasks.update_mailing_list_subscription(from_email_address, False)


@receiver(pre_delete, sender=User)
def user_pre_delete(sender, instance: User, **kwargs):
    """Delete the user from the newsletter."""

    if not hasattr(settings, 'ANYMAIL'):
        log.info("Mailgun not configured, skipping mailing list subscription update")
        return
    api_url_base = f"https://api.mailgun.net/v3"
    api_url_newsletter = f"{api_url_base}/lists/{settings.MAILING_LIST_NEWSLETTER_EMAIL}"
    requests.delete(
        f"{api_url_newsletter}/members/{instance.email}",
        auth=('api', settings.ANYMAIL['MAILGUN_API_KEY']),
    )
    log.info("Deleted user %i from mailing list" % instance.id)
