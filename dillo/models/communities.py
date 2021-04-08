from django.db import models
from django.urls import reverse

from dillo.models.mixins import get_upload_to_hashed_path, SocialLink


class Community(models.Model):

    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private'),
    )
    created_at = models.DateTimeField('Date created', auto_now_add=True)
    name = models.CharField(max_length=256, null=False)
    slug = models.SlugField()
    tagline = models.TextField(help_text='A short tagline.')
    description = models.TextField(help_text='Markdown describing the community.')
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default='unlisted')
    # Make community discoverable when not logged in
    is_featured = models.BooleanField(default=False)
    thumbnail = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='thumbnail_height',
        width_field='thumbnail_width',
        help_text='A 16:9 image to use for OpenGraph and others',
    )
    thumbnail_height = models.PositiveIntegerField(null=True)
    thumbnail_width = models.PositiveIntegerField(null=True)
    logo = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='logo_height',
        width_field='logo_width',
        help_text='A square image with the community logo',
    )
    logo_height = models.PositiveIntegerField(null=True)
    logo_width = models.PositiveIntegerField(null=True)

    header = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='header_height',
        width_field='header_width',
        help_text='A wide image',
    )
    header_height = models.PositiveIntegerField(null=True)
    header_width = models.PositiveIntegerField(null=True)

    theme_color = models.CharField(max_length=16, blank=True)

    dillo_uuid = models.SlugField(blank=True)

    def get_absolute_url(self):
        return reverse('community-detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'communities'


class CommunityLink(SocialLink):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='links')


class CommunityCategory(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ['community', 'slug']

    def __str__(self):
        return self.name
