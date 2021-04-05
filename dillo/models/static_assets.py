import pathlib
import urllib.parse
from django.contrib.auth.models import User
from django.db import models

from dillo.models.mixins import (
    get_upload_to_hashed_path,
    HashIdGenerationMixin,
    CreatedUpdatedMixin,
)


class StaticAsset(CreatedUpdatedMixin, HashIdGenerationMixin, models.Model):
    STATIC_ASSET_TYPES = (
        ('file', 'File'),
        ('image', 'Image'),
        ('video', 'Video'),
    )
    order = models.PositiveIntegerField(default=0)
    source = models.FileField(upload_to=get_upload_to_hashed_path, blank=True,)
    source_type = models.CharField(choices=STATIC_ASSET_TYPES, default='file', max_length=5)
    source_filename = models.CharField(max_length=256, editable=False, blank=True)
    size_bytes = models.BigIntegerField(editable=False, null=True)
    hash_id = models.CharField(max_length=6, unique=True, null=True)
    thumbnail = models.ImageField(
        blank=True, height_field='thumbnail_height', width_field='thumbnail_width'
    )
    thumbnail_height = models.PositiveIntegerField(null=True, blank=True)
    thumbnail_width = models.PositiveIntegerField(null=True, blank=True)
    slug = models.SlugField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        self._set_hash_id(created)
        if not created:
            return
        if self.source_type == 'video':
            Video.objects.create(static_asset=self)
        elif self.source_type == 'image':
            # Use source image as a thumbnail
            if not self.thumbnail:
                self.thumbnail.name = self.source.name
                self.save(update_fields=['thumbnail'])
            Image.objects.create(static_asset=self)

    def __str__(self):
        return f'{self.source_type} {self.id} - {self.source_filename}'.capitalize()


class Image(models.Model):
    """An image file."""

    class Meta:
        db_table = "dillo_staticasset_image"

    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    height = models.PositiveIntegerField(blank=True, null=True)
    width = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.static_asset.source_filename


class Video(models.Model):
    class Meta:
        db_table = "dillo_staticasset_video"

    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    framerate = models.FloatField(null=True)
    aspect = models.FloatField(null=True)
    encoding_job_id = models.IntegerField(null=True)
    encoding_job_status = models.CharField(max_length=128, null=True)
    encoding_job_progress = models.CharField(max_length=10, null=True, blank=True)
    # Amount of video loops views (hits to /v/<video_id>. This value
    # is atomically incremented in VideoViewsCountIncreaseView
    views_count = models.PositiveIntegerField(default=0)

    def replace_extension(self, extension):
        """Replace the extension of self.source.url."""
        # Parse the generated url (could look like an absolute path, or an actual url)
        url = urllib.parse.urlparse(self.static_asset.source.url)
        # Turn the path component into a Patlib path
        path = pathlib.Path(url.path)
        # Replace the extension
        path_with_suffix = str(path.with_suffix(extension))
        # Join the path back with the other components into a string url
        url = urllib.parse.urlunparse((url[0], url[1], path_with_suffix, url[3], url[4], url[5]))
        return url

    @property
    def url_720p(self):
        return self.replace_extension('.720p.mp4')

    @property
    def url_preview(self):
        return self.replace_extension('.preview.gif')

    def __str__(self):
        return self.static_asset.source_filename
