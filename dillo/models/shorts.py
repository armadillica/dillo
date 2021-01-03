import logging

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from taggit.managers import TaggableManager

from dillo.models.mixins import (
    get_upload_to_hashed_path,
    CreatedUpdatedMixin,
    LikesMixin,
    ChangeAwareness,
)
from dillo import tasks
from dillo.validators import validate_reel_url

log = logging.getLogger(__name__)


class Short(ChangeAwareness, CreatedUpdatedMixin, LikesMixin, models.Model):
    """A short film."""

    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='l_shorts')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    url = models.URLField(
        max_length=120,
        help_text='A YouTube or Vimeo link',
        validators=[validate_reel_url],
        unique=True,
    )
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default='public')
    image = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='image_height',
        width_field='image_width',
    )
    image_height = models.PositiveIntegerField(null=True)
    image_width = models.PositiveIntegerField(null=True)
    tags = TaggableManager()

    def get_absolute_url(self):
        return reverse('short-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Extend save() with video thumbnail fetching."""
        super().save(*args, **kwargs)

        if self.data_changed(['url']):
            log.debug('Updating thumbnail for short %i' % self.id)
            tasks.update_short_thumbnail(self.id)

    def __str__(self):
        return self.title
