import logging
import sorl.thumbnail

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.shortcuts import reverse

from dillo.models.mixins import (
    CreatedUpdatedMixin,
    HashIdGenerationMixin,
    get_upload_to_hashed_path,
)

from dillo.templatetags.dillo_filters import compact_naturaltime

from dillo.models.sorting import compute_hotness


log = logging.getLogger(__name__)


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
    is_pinned_by_moderator = models.BooleanField(default=False)
    hotness = models.FloatField(default=0)
    dillo_uuid = models.SlugField(blank=True, default='')
    image = models.ImageField(
        upload_to=get_upload_to_hashed_path, blank=True, help_text='A preview image for the entity',
    )

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        self._set_hash_id(created)

    def _update_hotness(self, ups: int, downs: int):
        """Based on votes, likes or any other property, update the hotness
        of an Entity.
        """
        if not self.published_at:
            return
        self.hotness = compute_hotness(ups, downs, self.published_at)
        self.save()
        return self.hotness

    def publish(self):
        """If the Entity is in 'draft', kick-off the publishing pipeline."""
        if self.status != 'draft':
            log.info(
                'Attempting to publish a %s %s, no action taken'
                % (self.status, self.content_type_name)
            )
            return

        # Set the Post as 'published'
        self.status = 'published'
        self.published_at = timezone.now()
        self._update_hotness(0, 0)
        self.save()
        log.info('Entity %s %i has been published' % (self.content_type_name, self.id))

    @property
    def content_type_id(self):
        return ContentType.objects.get_for_model(self).id

    @property
    def content_type_name(self):
        return ContentType.objects.get_for_model(self).name

    @property
    def is_edited(self):
        # Compare published and edit time in seconds to determine if the entity was edited
        value = (
            None
            if not self.published_at
            else self.published_at.strftime('%s') != self.updated_at.strftime('%s')
        )
        return value

    def serialized(self, request):
        """Return a serialized version of the core properties."""

        serialized_entity = {
            'user': {
                'name': self.user.profile.name,
                'username': self.user.username,
                'url': self.user.profile.absolute_url,
                'avatar': None,
                'likes_count': self.user.profile.likes_count,
                'badges': self.user.profile.serialized_badges,
            },
            'thumbnailUrl': None,
            'hashId': self.hash_id,
            'objectId': self.id,
            'contentTypeId': self.content_type_id,
            'isEditable': (self.user == request.user),
            'isEdited': self.is_edited,
            'datePublished': (
                None
                if not self.published_at
                else self.published_at.strftime('%a %d %b, %Y - %H:%M')
            ),
            'dateUpdated': (
                None if not self.updated_at else self.updated_at.strftime('%a %d %b, %Y - %H:%M')
            ),
            'naturalPublicationTime': (
                compact_naturaltime(self.updated_at)
                if not self.published_at
                else compact_naturaltime(self.published_at)
            ),
            'urlApiCommentListView': reverse(
                'api-comments-list',
                kwargs={
                    'entity_content_type_id': self.content_type_id,
                    'entity_object_id': self.id,
                },
            ),
        }

        # Generate thumbnail for user, if available
        if self.user.profile.avatar:
            serialized_entity['user']['avatar'] = sorl.thumbnail.get_thumbnail(
                self.user.profile.avatar, '128x128', crop='center', quality=80
            ).url

        return serialized_entity
