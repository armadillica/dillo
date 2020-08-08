import bleach
import datetime
import logging
import pathlib
import typing
import urllib.parse

import django.dispatch
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.contrib.sites.models import Site
from django.core.exceptions import FieldError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from model_utils.managers import InheritanceManagerMixin
from hashid_field import HashidField
from taggit.managers import TaggableManager

from dillo.models.mixins import (
    CreatedUpdatedMixin,
    LikesMixin,
    MentionsMixin,
    get_upload_to_hashed_path,
)
from dillo.tasks import create_job
from .communities import Community

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


class Post(InheritanceManagerMixin, CreatedUpdatedMixin, LikesMixin, MentionsMixin, models.Model):
    """A post created by a User.

    Features a title, some media, tags and mentions.
    """

    STATUSES = (
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('published', 'Published'),
    )
    VISIBILITIES = (
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private'),
    )
    # This value is set by the publish() method upon publishing
    published_at = models.DateTimeField('date published', null=True, blank=True)
    hash_id = HashidField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True)
    # TODO(fsiddi) rename to description
    title = models.TextField(null=True)
    content = models.TextField(null=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='draft')
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default='public')
    is_hidden_by_moderator = models.BooleanField(default=False)
    tags = TaggableManager()

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'hash_id': str(self.hash_id)})

    @property
    def absolute_url(self) -> str:
        return 'http://%s%s' % (Site.objects.get_current().domain, self.get_absolute_url())

    @property
    def comments_count(self) -> int:
        return Comment.objects.filter(post=self).count()

    @property
    def videos(self) -> typing.List['PostMediaVideo']:
        """Returns a list of PostMediaVideo objects."""
        media_video_type = ContentType.objects.get(app_label='dillo', model='postmediavideo')
        media_videos = []
        for video in self.postmedia_set.filter(content_type=media_video_type):
            media_videos.append(video.content_object)
        return media_videos

    @property
    def thumbnail(self):
        """An image preview for the Post, generated from the first media item.

        If the first media is an image, return the image.
        If the first media is a video, return the thumbnail.
        """
        first_media = self.postmedia_set.first()

        if not first_media:
            log.error('No thumbnail available for post %i' % self.id)
            return None

        if first_media.content_type.name == 'post media image':
            return first_media.content_object.image
        elif first_media.content_type.name == 'post media video':
            return first_media.content_object.thumbnail
        else:
            log.error('No thumbnail available for post %i' % self.id)
            return None

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
        log.debug('Found a processing video')
        if is_processing_videos:
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

    def process_video(self, video: 'PostMediaVideo'):
        """Set Post as 'processing' and start video encoding."""
        # Set status as processing, without triggering Post save signals
        Post.objects.filter(pk=self.id).update(status='processing')
        # Create a background job, using only hashable arguments
        create_job(str(self.hash_id), video.id, video.source.name)

    def update_video_processing_status(self, video_id: int, job: dict):
        """Update the processing status of a video.

        Called via the post_update_video_processing view, updates the
        the encoding_job_status and if the job status is 'job.completed'
        check if the Post itself is ready for publishing. If it is,
        kick off the publishing pipeline.
        """
        video = PostMediaVideo.objects.get(pk=video_id)
        if video.encoding_job_id != job['id']:
            # If the job id changed, we likely restarted the job (manually)
            video.encoding_job_status = None
            video.encoding_job_id = job['id']
            video.save()

        # If the current status of the video job is completed, we quit.
        # This prevents status updates sent after the completion of the job
        # from altering the video status.
        if video.encoding_job_status == 'job.completed':
            log.info('Encoding job was already completed')
            return

        # Update encoding job status
        job_status = job['event']
        job_progress = None if 'progress' not in job else job['progress']
        video.encoding_job_status = job_status
        video.encoding_job_progress = job_progress

        # Assign video thumbnail
        if 'format' in job and job['format'].startswith('jpg'):
            log.debug('Assigning thumbnail to video %i' % video_id)
            url = pathlib.Path(video.source.name)
            video.thumbnail = str(url.with_suffix('.thumbnail.jpg'))

        video.save()
        if job_status != 'job.completed':
            return
        if not self.may_i_publish:
            return
        log.debug('Video has been processed, attempting to publish')
        self.publish()

    def publish(self):
        """If the Post is in 'draft', kick-off the publishing pipeline."""
        if self.status != 'draft':
            log.info('Attempting to publish a %s Post, no action taken' % self.status)
            return

        # Set the Post as 'published'
        self.status = 'published'
        self.published_at = timezone.now()
        self.save()
        log.info('Post %i has been published' % self.id)

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


class PostLink(Post):
    pass


class PostJob(Post):
    CONTRACT_TYPES = (
        ('full-time', 'Full-time'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
    )

    company = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True)
    province_state = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255)
    contract_type = models.CharField(max_length=255, choices=CONTRACT_TYPES, default='full-time')
    is_remote_friendly = models.BooleanField(default=False)
    description = models.TextField(null=True)
    studio_website = models.URLField(max_length=120, blank=True)
    url_apply = models.URLField(max_length=550)
    software = models.CharField(max_length=256, blank=True)
    level = models.CharField(max_length=128, blank=True)
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

    def get_absolute_url(self):
        return reverse('job-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Override save in order to bleach the description."""
        self.description = bleach.clean(self.description)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'job'
        verbose_name_plural = 'jobs'


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
    source_metadata = JSONField(null=True)
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


class PostMedia(models.Model):
    limit = models.Q(app_label='dillo', model='PostMediaImage') | models.Q(
        app_label='dillo', model='PostMediaVideo'
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, limit_choices_to=limit, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return f'{self.content_type.name} {self.id}'.capitalize()


class Comment(CreatedUpdatedMixin, LikesMixin, MentionsMixin, models.Model):
    """A comment to Post or a reply to a Comment."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField(max_length=1024)
    tags = TaggableManager()

    @property
    def replies(self):
        return Comment.objects.filter(parent_comment_id=self.id).order_by('created_at')

    def get_absolute_url(self):
        post_url = reverse('post_detail', kwargs={'hash_id': str(self.post.hash_id)})
        return f'{post_url}#comment-{self.id}'

    @property
    def absolute_url(self) -> str:
        return 'http://%s%s' % (Site.objects.get_current().domain, self.get_absolute_url())

    def save(self, *args, **kwargs):
        if self.parent_comment and self.parent_comment.parent_comment:
            # The parent comment is actually a reply. This is not
            # allowed, since we only offer one-level deep conversations.
            log.error('Attemped to save a nested reply to comment %i' % self.parent_comment_id)
            raise FieldError('Nested replies to replies are not allowed')
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        comment_type = 'comment'
        if self.parent_comment:
            comment_type = 'reply'
        return f'a {comment_type} on "{self.post}"'
