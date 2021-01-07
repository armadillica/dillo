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


class ActionExtra(models.Model):
    action = models.OneToOneField(Action, on_delete=models.CASCADE, related_name='extra')
    parent_action = models.ForeignKey(
        Action, on_delete=models.CASCADE, null=True, blank=True, related_name='near_actions',
    )
    is_on_explore_feed = models.BooleanField(default=False)

    @property
    def near_actions_count(self):
        if self.is_parent:
            return ActionExtra.objects.filter(parent_action=self.action).count()
        else:
            return ActionExtra.objects.filter(parent_action=self.parent_action).count()

    @property
    def is_parent(self):
        return not self.parent_action

    class Meta:
        db_table = 'actstream_action_extra'

    def __str__(self):
        return 'ActionExtra: %s' % self.action
