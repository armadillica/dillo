import datetime
import logging
from actstream import models as models_actstream
from background_task import background
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from taggit import models as models_taggit

import dillo.models
import dillo.models.feeds
import dillo.models.posts
import dillo.views
from dillo.tasks.emails import send_notification_mail

log = logging.getLogger(__name__)


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
    for follower in models_actstream.followers(action.action_object.entity):
        if action.actor == follower:
            log.debug('Skipping notification generation post owner')
            continue
        log.debug(
            'Generating notification for user %i about comment %i'
            % (follower.id, action.action_object.id)
        )
        follower.feed_entries.create(action=action)
        # Email notification
        content_name = truncatechars(action.action_object.entity.title, 15)
        content_text = truncatechars(action.action_object.content, 25)
        comment_context = dillo.views.emails.CommentOrReplyContext(
            subject='Your post has a new comment!',
            own_name=follower.profile.first_name_guess or follower.username,
            own_profile_absolute_url=follower.profile.absolute_url,
            action_author_name=action.actor.profile.first_name_guess or action.actor.username,
            action_author_absolute_url=action.actor.profile.absolute_url,
            content_name=content_name,
            content_absolute_url=action.action_object.absolute_url,
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
        content_name = truncatechars(action.action_object.entity.title, 15)
        content_text = truncatechars(action.action_object.content, 25)
        reply_context = dillo.views.emails.CommentOrReplyContext(
            subject='Your comment has a new reply!',
            own_name=follower.profile.first_name_guess or follower.username,
            own_profile_absolute_url=follower.profile.absolute_url,
            action_author_name=action.actor.profile.first_name_guess or action.actor.username,
            action_author_absolute_url=action.actor.profile.absolute_url,
            content_name=content_name,
            content_absolute_url=action.action_object.absolute_url,
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


# TODO(fsiddi) turn this into a shared enum to use with action.send
fanout_functions = {
    'liked': feeds_fanout_liked,
    'commented': feeds_fanout_commented,
    'replied': feeds_fanout_replied,
    'started following': feeds_fanout_started_following,
    'posted': feeds_fanout_posted,
    'updated their reel': lambda _: None,
}


@background()
def activity_fanout_to_feeds(actstream_action_id):
    action = models_actstream.Action.objects.get(pk=actstream_action_id)
    log.debug('Processing "%s" action for feed fanout' % action.verb)
    if action.verb not in fanout_functions:
        return
    fanout_functions[action.verb](action)


@background()
def repopulate_timeline_content(content_type_id, object_id, user_id, action_verb):
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

    content_type = ContentType.objects.get_for_id(content_type_id)
    content_type_class = content_type.model_class()
    try:
        target = content_type.get_object_for_this_type(pk=object_id)
    except content_type_class.DoesNotExist:
        log.debug("Skipping timeline repopulation, content was deleted")
        return
    # If follow User
    if action_verb == 'follow' and isinstance(target, User):
        # If following user, get 10 posts and check if their creation activity is already in the
        # users timeline feed. If not, add push to the timeline
        actions = models_actstream.Action.objects.filter(verb='posted', actor_object_id=target.pk)[
            :10
        ]
        user = User.objects.get(pk=user_id)
        for action in actions:
            push_action_in_user_feed(user, action)
    elif action_verb == 'follow' and isinstance(target, models_taggit.Tag):
        # Get 10 posts with that tag
        posts = dillo.models.posts.Post.objects.filter(tags__name__in=[target.name])[:10]
        for post in posts:
            # Find post action (get only the first, as the same post could be
            # connected with multiple tags)
            action = models_actstream.Action.objects.filter(
                verb='posted', action_object_object_id=post.pk
            ).first()
            push_action_in_user_feed(User.objects.get(pk=user_id), action)
    # If unfollow User
    elif action_verb == 'unfollow' and isinstance(target, User):
        # Fetch all actions from the unfollowed users
        actions = models_actstream.Action.objects.filter(
            verb='posted', actor_object_id=target.pk
        ).all()
        # Fetch current user
        user = User.objects.get(pk=user_id)
        for action in actions:
            pull_action_from_user_feed(user, action)
    elif action_verb == 'unfollow' and isinstance(target, models_taggit.Tag):
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


def establish_time_proximity(action: models_actstream.Action):
    """Add Extra information a Post-related action.

    If a similar action (same actor, same object type, time delta less than 1h)
    was created, set the action_parent to said action.

    TODO(fsiddi): Refactor into add_extra_properties, with subfunctions for
    time proximity and feature in explore feed.
    """
    adjacent_action = (
        models_actstream.Action.objects.filter(
            actor_content_type=action.actor_content_type,
            actor_object_id=action.actor_object_id,
            verb=action.verb,
            action_object_content_type=action.action_object_content_type,
            timestamp__gte=(timezone.now() - datetime.timedelta(minutes=60)),
        )
        .exclude(pk=action.id)
        .order_by('-timestamp')
        .first()
    )
    parent_action = None

    if adjacent_action:
        adjancent_timeline_entry = dillo.models.feeds.ActionExtra.objects.filter(
            action=adjacent_action
        ).first()
        if not adjancent_timeline_entry:
            log.error('Missing adjacent timeline entry for action %i' % action.id)
        else:
            parent_action = (
                adjancent_timeline_entry.parent_action or adjancent_timeline_entry.action
            )

    log.debug('Adding extra info to action %i' % action.id)
    dillo.models.feeds.ActionExtra.objects.create(
        action=action, parent_action=parent_action, is_on_explore_feed=True
    )


if settings.BACKGROUND_TASKS_AS_FOREGROUND:
    # Will execute activity_fanout_to_feeds immediately
    log.debug('Executing background tasks synchronously')
    activity_fanout_to_feeds = activity_fanout_to_feeds.task_function
    repopulate_timeline_content = repopulate_timeline_content.task_function
