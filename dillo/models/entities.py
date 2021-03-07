from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models

from dillo.models.mixins import CreatedUpdatedMixin, HashIdGenerationMixin


class Entity(HashIdGenerationMixin, CreatedUpdatedMixin, models.Model):
    class Meta:
        abstract = True

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

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        self._set_hash_id(created)

    @property
    def content_type_id(self):
        return ContentType.objects.get_for_model(self).id
