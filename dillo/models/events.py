from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from dillo.models.entities import Entity


class Event(Entity):
    """A community event, which can be attended by users.

    Events can be only created by admin users.
    """

    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(null=False, unique=True)
    description = models.TextField(null=True)
    is_online = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True)
    website = models.URLField(max_length=120)
    starts_at = models.DateTimeField('starts at')
    ends_at = models.DateTimeField('ends at')
    # Use to allow users to mark themselves as "attending" an event
    attendees = models.ManyToManyField(User, related_name='events')

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'slug': self.slug})

    def is_attended(self, user: User):
        if user.is_anonymous:
            return False
        return user in self.attendees.all()

    def __str__(self):
        return self.name
