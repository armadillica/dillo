from actstream.models import Action
from django.contrib.auth.models import User
from django.db import models


class FeedEntry(models.Model):
    """Activity entries associate with a User.

    The Activities are categorized as 'notification', 'timeline' or
    'email' so they can be properly displayed (or mailed) to the User.
    Population of this table happens via actstream Action hooks, based
    on the Follow relationship that a User has with an actor.
    """

    CATEGORIES = (
        ('notification', 'Notification'),
        ('timeline', 'Timeline'),
        ('email', 'Email'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_entries')
    is_read = models.BooleanField(default=False)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    created_at = models.DateTimeField('date created', auto_now_add=True)
    updated_at = models.DateTimeField('date edited', auto_now=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='notification')
    # TODO(fsiddi) consider adding weight for improved grouping and sorting

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return 'FeedEntry: %s %s' % (self.action.actor, self.action.verb)
