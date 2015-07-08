from application import db

from application.modules.notifications.model import Notification
from application.modules.notifications.model import NotificationObject
from application.modules.notifications.model import NotificationSubscriptions

def notification_subscribe(object_type_id, object_id, user_id):
    """Subscribe a user to changes for a specific object. We create a subscription
    if none is found.

    :param object_type_id: hardcoded index, check the notifications/model.py
    :param object_id: object id, to be traced with object_type_id
    :param user_id: id of the user we are going to subscribe
    """
    subscription = NotificationSubscriptions.query\
        .filter(NotificationSubscriptions.object_type_id == object_type_id)\
        .filter(NotificationSubscriptions.object_id == object_id)\
        .filter(NotificationSubscriptions.user_id == user_id)\
        .first()

    # If no subscription exists, we create one
    if not subscription:
        notification_subscription = NotificationSubscriptions(
            object_type_id=object_type_id,
            object_id=object_id,
            user_id=user_id)
        db.session.add(notification_subscription)
        db.session.commit()


def notification_object_add(object_type_id, object_id, actor_user_id, verb):
    """Add a notification object and creates a notification for each user that
    - is not the original author of the post
    - is actively subscribed to the object

    :param object_type_id: hardcoded index, check the notifications/model.py
    :param object_id: object id, to be traced with object_type_id
    :param actor_user_id: id of the user who is changing the object
    :param verb: the action on the object ('commented', 'replied')
    """
    subscriptions = NotificationSubscriptions.query\
        .filter(NotificationSubscriptions.object_type_id == object_type_id)\
        .filter(NotificationSubscriptions.object_id == object_id)\
        .filter(NotificationSubscriptions.user_id != actor_user_id)\
        .filter(NotificationSubscriptions.is_subscribed == True)\
        .all()

    if subscriptions:
        notification_object = NotificationObject(
            object_type_id=object_type_id,
            object_id=object_id,
            actor_user_id=actor_user_id,
            verb=verb)
        db.session.add(notification_object)
        db.session.commit()

        for subscription in subscriptions:
            notification = Notification(
                user_id=subscription.user_id,
                notification_object_id=notification_object.id)
            db.session.add(notification)
            db.session.commit()
