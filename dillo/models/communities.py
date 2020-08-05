from django.contrib.auth.models import User
from django.db import models


class Community(models.Model):
    """A Community. A Post belongs to a Community."""

    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private'),
    )
    created_at = models.DateTimeField('Date created', auto_now_add=True)
    name = models.CharField(max_length=256, null=False)
    slug = models.SlugField()
    tagline = models.TextField()
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default='unlisted')
    # Make community discoverable when not logged in
    is_featured = models.BooleanField(default=False)
