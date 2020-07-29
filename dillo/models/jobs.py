import bleach
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from taggit.managers import TaggableManager

from dillo.models.mixins import get_upload_to_hashed_path, CreatedUpdatedMixin, LikesMixin


class Job(CreatedUpdatedMixin, LikesMixin, models.Model):
    """A Job offer."""

    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
    )

    CONTRACT_TYPES = (
        ('full-time', 'Full-time'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    company = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True)
    province_state = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255)
    title = models.CharField(max_length=255, help_text='E.g. Animation Director')
    contract_type = models.CharField(max_length=255, choices=CONTRACT_TYPES, default='full-time')
    is_remote_friendly = models.BooleanField(default=False)
    description = models.TextField(null=True)
    studio_website = models.URLField(max_length=120, blank=True)
    url_apply = models.URLField(max_length=550)
    software = models.CharField(max_length=256, blank=True)
    level = models.CharField(max_length=128, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default='public')
    starts_at = models.DateField('starts at', blank=True, null=True)
    notes = models.TextField(null=True)
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
        return reverse('job-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Override save in order to bleach the description."""
        self.description = bleach.clean(self.description)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} at {self.company}"
