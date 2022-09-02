import logging
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from taggit.managers import TaggableManager

from dillo.models.mixins import CreatedUpdatedMixin, LikesMixin, MentionsMixin, SpamDetectMixin

log = logging.getLogger(__name__)


class Comment(CreatedUpdatedMixin, LikesMixin, MentionsMixin, SpamDetectMixin, models.Model):
    """A comment to an Entity or a reply to a Comment."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    entity_object_id = models.PositiveIntegerField(null=True)
    # Content object should be a subclass of Entity
    entity = GenericForeignKey('entity_content_type', 'entity_object_id')
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField(max_length=1024)
    slug = models.SlugField(blank=True)
    tags = TaggableManager()

    spam_detect_field_names = ['content']

    @property
    def is_edited(self):
        # Compare creation and edit time in seconds to determine if
        # the comment was edited
        return self.created_at.strftime('%s') != self.updated_at.strftime('%s')

    @property
    def replies(self):
        return Comment.objects.filter(parent_comment_id=self.id).order_by('created_at')

    def get_absolute_url(self):
        entity_url = self.entity.get_absolute_url()
        return f'{entity_url}#comment-{self.id}'

    @property
    def absolute_url(self) -> str:
        return 'http://%s%s' % (Site.objects.get_current().domain, self.get_absolute_url())

    def save(self, *args, **kwargs):
        if self.parent_comment and self.parent_comment.parent_comment:
            # The parent comment is actually a reply. This is not
            # allowed, since we only offer one-level deep conversations.
            log.error('Attempted to save a nested reply to comment %i' % self.parent_comment_id)
            self.parent_comment = self.parent_comment.parent_comment
            # raise FieldError('Nested replies to replies are not allowed')
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        comment_type = 'comment'
        if self.parent_comment:
            comment_type = 'reply'
        return f'a {comment_type} on "{self.entity}"'
