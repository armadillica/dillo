import logging
import sorl.thumbnail

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db import models
from django.utils import timezone
from django.shortcuts import reverse

from dillo.models.mixins import CreatedUpdatedMixin, HashIdGenerationMixin


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

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        self._set_hash_id(created)

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
        self.save()
        log.info('Entity %s %i has been published' % (self.content_type_name, self.id))

    @property
    def content_type_id(self):
        return ContentType.objects.get_for_model(self).id

    @property
    def content_type_name(self):
        return ContentType.objects.get_for_model(self).name

    def serialized(self, request):
        """Return a serialized version of the core properties."""

        serialized_entity = {
            'user': {
                'name': self.user.profile.name,
                'username': self.user.username,
                'url': self.user.profile.absolute_url,
                'avatar': None,
            },
            'thumbnailUrl': None,
            'hashId': self.hash_id,
            'objectId': self.id,
            'contentTypeId': self.content_type_id,
            'isEditable': (self.user == request.user),
            'datePublished': (
                None if not self.published_at else self.published_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            ),
            'naturalPublicationTime': naturaltime(self.published_at),
            'urlApiCommentLisView': reverse(
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
