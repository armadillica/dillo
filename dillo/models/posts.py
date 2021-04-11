import datetime
import logging
import pathlib
import typing
import urllib.parse

import django.dispatch
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from django.utils import timezone
from taggit.managers import TaggableManager

from dillo.models.mixins import (
    LikesMixin,
    MentionsMixin,
    get_upload_to_hashed_path,
    HashIdGenerationMixin,
)
from dillo.tasks import create_coconut_job
from .communities import Community, CommunityCategory
from .entities import Entity
from dillo.models.static_assets import StaticAsset, Image, Video
from dillo.templatetags.dillo_filters import website_hostname

log = logging.getLogger(__name__)


# Custom signal to trigger activity generation based on parsed Tags.
post_published = django.dispatch.Signal(providing_args=["instance"])


def get_trending_tags():
    """Find the top 10 used tags since the past 15 days.

    We query all Posts created in the past 15 days, aggregate, count and
    sort the Tags.
    """
    time_delta_in_days = 15
    time_limit = timezone.now() - datetime.timedelta(days=time_delta_in_days)
    tags = Post.tags.most_common(
        extra_filters={'post__created_at__gte': time_limit, 'post__visibility': 'public'}
    )[:10]
    if not tags:
        log.debug("No recent common tags found, querying all tags")
        tags = Post.tags.most_common()[:10]
    return tags


def extract_hash_tags(s):
    return set(part[1:] for part in s.split() if part.startswith('#'))


class Post(Entity, LikesMixin, MentionsMixin):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    is_link = models.BooleanField(default=False, blank=True)
    is_hidden_by_moderator = models.BooleanField(default=False)
    tags = TaggableManager()
    categories = models.ManyToManyField(CommunityCategory, blank=True)
    comments = GenericRelation(
        'dillo.Comment',
        object_id_field='entity_object_id',
        content_type_field='entity_content_type',
        related_query_name='post',
    )
    media = models.ManyToManyField(StaticAsset, related_name='post', blank=True)

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'hash_id': str(self.hash_id)})

    @property
    def absolute_url(self) -> str:
        return 'http://%s%s' % (Site.objects.get_current().domain, self.get_absolute_url())

    @property
    def link_favicon(self):
        if self.is_link and self.content:
            domain = urllib.parse.urlparse(self.content).netloc
            return f"https://www.google.com/s2/favicons?domain={domain}"

    @property
    def link_hostname(self):
        if self.is_link and self.content:
            hostname = website_hostname(self.content)
            return hostname

    @property
    def videos(self) -> typing.List['Video']:
        """Returns a list of Video objects."""
        return [static_asset.video for static_asset in self.media.filter(source_type='video')]

    @property
    def thumbnail(self):
        """An image preview for the Post.

        If the post as an image, use it.
        If the first media is an image, return the image.
        If the first media is a video, return the thumbnail.
        """
        if self.image:
            return self.image
        first_media = self.media.filter(source_type__in=['video', 'image']).first()
        if not first_media:
            log.error('No thumbnail available for post %i' % self.id)
            return None
        return first_media.thumbnail

    @property
    def may_i_publish(self):
        """Investigate the status of attached videos.

        If video.encoding_job_status is 'job.complete' for all videos,
        we set the post status to 'draft' and we are ready for publishing.
        """
        if not self.videos:
            return True
        is_processing_videos = False
        for video in self.videos:
            log.debug('Checking processing status of encoded videos')
            if video.encoding_job_status != 'job.completed':
                is_processing_videos = True
                break
        if is_processing_videos:
            log.debug('Found a processing video')
            return False
        log.debug('All videos are encoded')
        self.status = 'draft'
        self.save()
        log.info('Post %i has status %s and is ready for publishing' % (self.id, self.status))
        return True

    def process_videos(self) -> int:
        """Look at attached media, and if videos are present, start processing.

        Returns an int, used in the admin to show how many video are processed.
        """
        videos_processing_count = 0
        for video in self.videos:
            # Create encoding job for the video
            self.process_video(video)
            videos_processing_count += 1
        return videos_processing_count

    def process_video(self, video: Video):
        """Set Post as 'processing' and start video encoding."""
        # Set status as processing, without triggering Post save signals
        Post.objects.filter(pk=self.id).update(status='processing')
        # Create a background job, using only hashable arguments
        create_coconut_job(str(self.hash_id), video.id)

    def publish(self):
        super(Post, self).publish()

        # Send signal to generate Tags activity
        post_published.send(sender=self.__class__, instance=self)

    def is_bookmarked(self, user: User):
        if user.is_anonymous:
            return False
        return user.profile.bookmarks.filter(pk=self.pk).exists()

    def __str__(self):
        return f'{self.title[:50]}' if self.title else str(self.hash_id)

    class Meta:
        ordering = ['-created_at']


class PostMediaImage(models.Model):
    """An image file, attached to a Post via PostMedia."""

    image = models.ImageField(
        upload_to=get_upload_to_hashed_path, blank=True, height_field='height', width_field='width',
    )
    height = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    source_filename = models.CharField(max_length=128, null=True)

    def __str__(self):
        return self.source_filename


class PostMediaVideo(models.Model):
    """Videos will be available as video_mp4_720p and video_stream."""

    source = models.FileField(upload_to=get_upload_to_hashed_path, blank=True,)
    # video = models.FilePathField(
    #     blank=True,
    # )
    source_metadata = JSONField(null=True, blank=True)
    source_filename = models.CharField(max_length=128, null=True)
    framerate = models.FloatField(null=True)
    aspect = models.FloatField(null=True)
    encoding_job_id = models.IntegerField(null=True)
    encoding_job_status = models.CharField(max_length=128, null=True)
    encoding_job_progress = models.CharField(max_length=10, null=True, blank=True)
    thumbnail = models.ImageField(
        blank=True, height_field='thumbnail_height', width_field='thumbnail_width'
    )
    thumbnail_height = models.PositiveIntegerField(null=True, blank=True)
    thumbnail_width = models.PositiveIntegerField(null=True, blank=True)
    # Amount of video loops views (hits to /v/<video_id>. This value
    # is atomically incremented in VideoViewsCountIncreaseView
    views_count = models.PositiveIntegerField(default=0)

    def replace_extension(self, extension):
        """Replace the extension of self.source.url."""
        # Parse the generated url (could look like an absolute path, or an actual url)
        url = urllib.parse.urlparse(self.source.url)
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
        return self.source_filename


class PostMedia(HashIdGenerationMixin, models.Model):
    limit = models.Q(app_label='dillo', model='PostMediaImage') | models.Q(
        app_label='dillo', model='PostMediaVideo'
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, limit_choices_to=limit, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    hash_id = models.CharField(max_length=6, unique=True, null=True)

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        self._set_hash_id(created)

    def __str__(self):
        return f'{self.content_type.name} {self.id}'.capitalize()
