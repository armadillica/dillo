import bleach
from django.db import models
from django.urls import reverse

from dillo.models.mixins import get_upload_to_hashed_path
from dillo.models.posts import Post


class Software(models.Model):
    name = models.CharField(max_length=128)

    # TODO(fsiddi) Add url, and logo/favicon

    def __str__(self):
        return self.name


class PostRig(Post):
    """A Rig character."""

    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
    )

    # Use author to attribute the rig to someone else than the user submitting the rig
    author = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, help_text='The name of the character')
    description = models.TextField(null=True)
    url = models.URLField(max_length=550, help_text='Where to get the rig (Gumroad, Dropbox, etc.)')
    notes = models.TextField(null=True, blank=True)
    image = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='image_height',
        width_field='image_width',
        help_text='A 16:9 preview of the rig',
    )
    image_height = models.PositiveIntegerField(null=True)
    image_width = models.PositiveIntegerField(null=True)
    software = models.ManyToManyField(
        Software, related_name='software', blank=True, help_text='Software compatibility'
    )

    @property
    def supported_software(self):
        return self.software.all()

    def get_absolute_url(self):
        return reverse('rig-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Override save in order to bleach the description."""
        self.description = bleach.clean(self.description)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
