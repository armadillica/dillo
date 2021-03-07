import hashlib
import pathlib
import urllib.parse
import uuid
import logging
from dataclasses import dataclass, field
from hashids import Hashids


from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.urls import reverse

log = logging.getLogger(__name__)
hashids = Hashids(min_length=4)


def get_social_from_url(url):
    """Used when parsing links in ProfileLink and CommunityLink"""
    supported_domains = {
        'artstation.com',
        'facebook.com',
        'instagram.com',
        'linkedin.com',
        'patreon.com',
        'twitch.tv',
        'twitter.com',
        'vimeo.com',
        'youtube.com',
    }
    hostname = urllib.parse.urlparse(url).hostname
    # We iterate over the domains instead of looking up the hostname in the supported_domains
    # list because a hostname could be instagram.com or www.instagram.com
    for s in supported_domains:
        if s in hostname:
            log.debug('Found %s in social url' % hostname)
            return s.split('.')[0]
    log.debug('No social found in %s' % hostname)
    return ''


def generate_hash_from_filename(filename):
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = str(uuid.uuid4()) + filename
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


def get_upload_to_hashed_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/<bd>/<bd2b5b1cd81333ed2d8db03971f91200>
    extension = pathlib.Path(filename).suffix
    hashed = generate_hash_from_filename(filename)

    path = pathlib.Path(hashed[:2], hashed[2:4])
    if instance._meta.model_name == 'postmediavideo':
        path = path.joinpath(hashed, hashed).with_suffix(extension)
    else:
        path = path.joinpath(hashed).with_suffix(extension)
    return path


class CreatedUpdatedMixin(models.Model):
    """Store creation and update timestamps."""

    class Meta:
        abstract = True

    created_at = models.DateTimeField('date created', auto_now_add=True)
    updated_at = models.DateTimeField('date edited', auto_now=True)


class LikesMixin(models.Model):
    """Methods for Posts and Comments that allow liking."""

    class Meta:
        abstract = True

    likes = GenericRelation('dillo.Likes')

    @property
    def content_type_id(self):
        return ContentType.objects.get_for_model(self).id

    @property
    def like_toggle_url(self):
        return reverse(
            'like_toggle', kwargs={'content_type_id': self.content_type_id, 'object_id': self.id}
        )

    def is_liked(self, user: User):
        if user.is_anonymous:
            return False
        return Likes.objects.filter(
            user=user, content_type_id=ContentType.objects.get_for_model(self), object_id=self.id
        ).exists()

    def like_toggle(self, user: User) -> (str, str, str):
        """Like or unlike an instance.

        Returns a tuple that is used as response in the AJAX request that
        calls the toggle. The components are:
        - action: used in the JS code to add or remove attributes
        - action_label: to replace the label of the like button, if present
        - likes_count: to replace the label of the likes count
        - likes_word: to combine with likes count and replate the likes count label
        """
        if user.is_anonymous:
            raise SuspiciousOperation('Anonymous user tried to like an item')
        content_type_id = self.content_type_id
        if self.is_liked(user):
            action = "unliked"
            # TODO(fsiddi) add translation
            action_label = 'Unliked'
            # Will generate a signal dillo.signals.on_create_like
            Likes.objects.get(
                user=user, content_type_id=content_type_id, object_id=self.id
            ).delete()
        else:
            action = "liked"
            action_label = 'Liked'
            # Will generate a signal signal dillo.signals.on_deleted_like
            Likes.objects.create(user=user, content_object=self)

        # Generate likes count label (used to update the interface)
        likes_count = self.likes.count()
        likes_word = 'LIKE'
        if likes_count != 1:
            likes_word = 'LIKES'

        log.info('User %i %s %i %i' % (user.id, action, content_type_id, self.id))
        return action, action_label, likes_count, likes_word


class MentionsMixin(models.Model):
    """Methods to expose mentions in Posts and Comments."""

    class Meta:
        abstract = True

    @property
    def content_type_id(self):
        return ContentType.objects.get_for_model(self).id

    @property
    def mentioned_users(self):
        mentions = Mentions.objects.filter(content_type_id=self.content_type_id, object_id=self.id)
        return [mention.user for mention in mentions]


class Likes(models.Model):
    limit = (
        models.Q(app_label='dillo', model='Post')
        | models.Q(app_label='dillo', model='Comment')
        | models.Q(app_label='dillo', models='Short')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, limit_choices_to=limit, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return f'Like by {self.user}'


class Mentions(models.Model):
    """Mentions of a User in a Post or Comment."""

    limit = models.Q(app_label='dillo', model='Post') | models.Q(app_label='dillo', model='Comment')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, limit_choices_to=limit, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return f'Mention in {self.content_object}'


class ChangeAwareness(models.Model):
    """Functionality to detect changes on model save."""

    class Meta:
        abstract = True

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._state.adding = False
        instance._state.db = db
        instance._old_values = dict(zip(field_names, values))
        return instance

    def data_changed(self, fields):
        """Check if data has changed in the model.

        Returns True if the model saved the first time and _old_values doesnt exist

        :param fields: A list of model fields
        :return:
        """
        if hasattr(self, '_old_values'):
            if not self.pk or not self._old_values:
                return True

            for field in fields:
                if getattr(self, field) != self._old_values[field]:
                    return True
            return False

        return True


@dataclass
class ApiResponseData:
    """Standard API response content."""

    results: list = field(default_factory=list)
    count: int = 0
    next_page_number: int = None

    def serialize(self) -> dict:
        return {
            'results': self.results,
            'count': self.count,
            'nextPageNumber': self.next_page_number,
        }


class HashIdGenerationMixin(models.Model):
    class Meta:
        abstract = True

    def _set_hash_id(self, created=False):
        if not created:
            return
        self.__class__.objects.filter(pk=self.pk).update(hash_id=hashids.encode(self.pk))
