import datetime
from application import db


class Notification(db.Model):
    """Basic notification. We create one notification per object per user.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer(),
        db.ForeignKey('user.id'), nullable=False)
    notification_object_id = db.Column(db.Integer(),
        db.ForeignKey('notification_object.id'), nullable=False)
    notification_object = db.relationship('NotificationObject',
        backref=db.backref('notification'))
    is_read = db.Column(db.Boolean(), default=False)
    date_read = db.Column(db.DateTime())

    def __str__(self):
        return u"Notification {0}".format(self.id)


class NotificationObject(db.Model):
    """Upon changes of an object we can create a notification object, informing
    subscribed users of the changes (comment was added, reply was added, etc).
    For performance we rely on hardcoded ids for object types, where the initial
    one are:
    1) posts
    2) comments
    """
    id = db.Column(db.Integer, primary_key=True)
    # 1: post, 2: comment
    object_type_id = db.Column(db.Integer(), nullable=False)
    object_id = db.Column(db.Integer(), nullable=False)
    actor_user_id = db.Column(db.Integer(),
        db.ForeignKey('user.id'), nullable=False)
    verb = db.Column(db.String(64), nullable=False)
    context_object_type_id = db.Column(db.Integer())
    context_object_id = db.Column(db.Integer())
    date_creation = db.Column(db.DateTime(), default=datetime.datetime.now)

    def __str__(self):
        return u"NotificationObject {0}".format(self.id)


class NotificationSubscriptions(db.Model):
    """For every object supporting subscriptions, we create an relation with
    each user interactig with it.
    """
    id = db.Column(db.Integer, primary_key=True)
    # 1: post, 2: comment
    context_object_type_id = db.Column(db.Integer(), nullable=False)
    context_object_id = db.Column(db.Integer(), nullable=False)
    user_id = db.Column(db.Integer(),
        db.ForeignKey('user.id'), nullable=False)
    is_subscribed = db.Column(db.Boolean(), default=True)

    def __str__(self):
        return u"NotificationSubscription {0}".format(self.id)

