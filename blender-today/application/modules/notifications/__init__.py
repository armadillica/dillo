from flask import render_template
from flask import Blueprint
from flask import jsonify
from flask import url_for
from flask import abort
from flask import request

from flask.ext.security import login_required
from flask.ext.security import current_user

from application import app
from application import db

from application.modules.posts.model import Post, Comment
from application.modules.users.model import User
from application.modules.notifications.model import Notification
from application.modules.notifications.model import NotificationObject
from application.modules.notifications.model import NotificationSubscriptions

notifications = Blueprint('notifications', __name__)

def notification_subscribe(user_id, context_object_type_id, context_object_id):
    """Subscribe a user to changes for a specific context. We create a subscription
    if none is found.

    :param user_id: id of the user we are going to subscribe
    :param context_object_type_id: hardcoded index, check the notifications/model.py
    :param context_object_id: object id, to be traced with context_object_type_id
    """
    subscription = NotificationSubscriptions.query\
        .filter(NotificationSubscriptions.context_object_type_id == context_object_type_id)\
        .filter(NotificationSubscriptions.context_object_id == context_object_id)\
        .filter(NotificationSubscriptions.user_id == user_id)\
        .first()

    # If no subscription exists, we create one
    if not subscription:
        notification_subscription = NotificationSubscriptions(
            context_object_type_id=context_object_type_id,
            context_object_id=context_object_id,
            user_id=user_id)
        db.session.add(notification_subscription)
        db.session.commit()


def notification_object_add(actor_user_id, verb, object_type_id, object_id,
        context_object_type_id, context_object_id):
    """Add a notification object and creates a notification for each user that
    - is not the original author of the post
    - is actively subscribed to the object

    This works using the following pattern:

    ACTOR -> VERB -> OBJECT -> CONTEXT

    :param actor_user_id: id of the user who is changing the object
    :param verb: the action on the object ('commented', 'replied')
    :param object_type_id: hardcoded index, check the notifications/model.py
    :param object_id: object id, to be traced with object_type_id
    """
    subscriptions = NotificationSubscriptions.query\
        .filter(NotificationSubscriptions.context_object_type_id == context_object_type_id)\
        .filter(NotificationSubscriptions.context_object_id == context_object_id)\
        .filter(NotificationSubscriptions.user_id != actor_user_id)\
        .filter(NotificationSubscriptions.is_subscribed == True)\
        .all()

    if subscriptions:
        notification_object = NotificationObject(
            actor_user_id=actor_user_id,
            verb=verb,
            object_type_id=object_type_id,
            object_id=object_id,
            context_object_type_id=context_object_type_id,
            context_object_id=context_object_id
            )
        db.session.add(notification_object)
        db.session.commit()

        for subscription in subscriptions:
            notification = Notification(
                user_id=subscription.user_id,
                notification_object_id=notification_object.id)
            db.session.add(notification)
            db.session.commit()


def notification_parse(notification):
    notification_object = NotificationObject.query\
        .get(notification.notification_object_id)

    actor = User.query.get_or_404(notification_object.actor_user_id)

    # Context is optional
    context_object_type = None
    context_object_name = None
    context_object_url = None

    if notification_object.object_type_id == 2:
        # Initial support only for comments
        comment = Comment.query.get_or_404(notification_object.object_id)
        post = comment.post
        object_type = 'comment'
        object_name = ""
        post_url = url_for('posts.view',
            category=post.category.url,
            uuid=post.uuid,
            slug=post.slug,
            )
        # Handmade anchor appended to url
        object_url = "{0}#comment-{1}".format(post_url, comment.id)

        if comment.parent_id:
            context_object_type = 'comment'
            context_object_name = None
            context_object_url = "{0}#comment-{1}".format(
                post_url, comment.parent_id)
        else:
            context_object_type = 'post'
            context_object_name = post.title
            context_object_url = post_url

    return dict(
        _id=notification.id,
        username=actor.username,
        username_avatar=actor.gravatar(),
        username_url=url_for('users.view', user_id=actor.id),
        action=notification_object.verb,
        object_type=object_type,
        object_name=object_name,
        object_url=object_url,
        context_object_type=context_object_type,
        context_object_name=context_object_name,
        context_object_url=context_object_url,
        date=notification_object.date_creation,
        is_read=notification.is_read,
        is_subscribed=notification.is_subscribed)


@notifications.route('/')
@login_required
def index():
    """Get notifications for the current user.

    Optional url args:
    - limit: limits the number of notifications
    - format: html or JSON
    """
    limit = request.args.get('limit', 20)
    notifications = Notification.query\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.id.desc())\
        .limit(limit)
    items = []
    for notification in notifications:
        items.append(notification_parse(notification))

    return jsonify(items=items)


@notifications.route('/<int:notification_id>/read-toggle')
@login_required
def action_read_toggle(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        if notification.is_read:
            notification.is_read = False
        else:
            notification.is_read = True
        db.session.commit()
        return jsonify(message="Updated notification {0}".format(notification_id))
    else:
        return abort(403)


@notifications.route('/<int:notification_id>/subscription-toggle')
@login_required
def action_subscription_toggle(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification_subscription = notification.get_subscription()
        if notification_subscription:
            if notification_subscription.is_subscribed:
                notification_subscription.is_subscribed = False
                action = "Unsubscribed"
            else:
                notification_subscription.is_subscribed = True
                action = "Subscribed"
            db.session.commit()
            return jsonify(message="{0} from notifications".format(action))
        else:
            return jsonify(message="No subscription exists")
    else:
        return abort(403)

