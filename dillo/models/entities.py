from django.contrib.auth.models import User
from django.db import models

from dillo.models.mixins import CreatedUpdatedMixin


class Entity(CreatedUpdatedMixin, models.Model):
    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private'),
    )
    STATUSES = (
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('published', 'Published'),
    )

    hash_id = models.CharField(max_length=20, blank=True)
    published_at = models.DateTimeField('date published', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUSES, default='draft')
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default='public')

    class Meta:
        abstract = True
