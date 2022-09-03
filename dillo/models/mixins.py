import hashlib
import pathlib
import typing
import urllib.parse
import uuid
import logging
import re
from dataclasses import dataclass, field
from hashids import Hashids

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import SuspiciousOperation
from django.core.signing import Signer, BadSignature
from django.db import models
from django.urls import reverse
from django.utils import timezone
from urlextract import URLExtract

from dillo.models.moderation import SpamWord, AllowedDomain


log = logging.getLogger(__name__)
hashids = Hashids(min_length=4)


def get_social_from_url(url):
    """Used when parsing links in ProfileLink and CommunityLink"""
    supported_domains = {
        'anima.to',
        'artstation.com',
        'blender.community',
        'discord.gg',
        'facebook.com',
        'github.com',
        'gitlab.com',
        'instagram.com',
        'linkedin.com',
        'patreon.com',
        'tiktok.com',
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
    # Create a path that looks like this
    # a4/a4955e4f68e22a095422e1286d95a5a7/a4955e4f68e22a095422e1286d95a5a7.jpg
    file_path = pathlib.Path(filename)
    hashed_path = generate_hash_from_filename(file_path.name)
    path = (
        pathlib.Path(hashed_path[:2])
        .joinpath(hashed_path)
        .joinpath(hashed_path)
        .with_suffix(file_path.suffix)
    )
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
    def is_hot(self):
        return self.likes.count() > 10

    @property
    def content_type_id(self):
        return ContentType.objects.get_for_model(self).id

    @property
    def like_toggle_url(self):
        return reverse(
            'like_toggle', kwargs={'content_type_id': self.content_type_id, 'object_id': self.id}
        )

    def update_hotness(self) -> typing.Optional[float]:
        return None

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

        # Always try to update hotness. If the class using this mixing does
        # not override the update_hotness method, nothing will happen.
        if self.update_hotness():
            log.debug('Updated hotness for item')
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


class SocialLink(models.Model):
    """Base class to handle social links."""

    class Meta:
        abstract = True

    url = models.URLField(help_text='YouTube, Instagram, Twitter...', verbose_name="URL")
    social = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        if not self.social:
            self.social = get_social_from_url(self.url)
        super().save(*args, **kwargs)


@dataclass
class ApiResponseData:
    """Standard API response content."""

    results: list = field(default_factory=list)
    count: int = 0
    next_page_number: int = None
    url_next_page: str = None

    def serialize(self) -> dict:
        return {
            'results': self.results,
            'count': self.count,
            'nextPageNumber': self.next_page_number,
            'urlNextPage': self.url_next_page,
        }


class HashIdGenerationMixin(models.Model):
    class Meta:
        abstract = True

    def _set_hash_id(self, created=False):
        if not created:
            return
        self.__class__.objects.filter(pk=self.pk).update(hash_id=hashids.encode(self.pk))


class Downloadable(models.Model):
    class Meta:
        abstract = True

    downloadable = models.ForeignKey(
        'dillo.StaticAsset',
        on_delete=models.CASCADE,
        related_name='+',
        blank=True,
        null=True,
    )

    def check_downloadable_signed_url(self, url) -> bool:
        """
        :param url: signed url (absolute path)
        returns True
        get signed url, expected to be in the format
        /path/?signature=<signature>&expires=<expires>
        check signature and expires timestamp
        return True if ok
        """
        parsed_url = urllib.parse.urlparse(url)
        query_dict = urllib.parse.parse_qs(parsed_url.query)

        try:
            signature = query_dict['signature'][0]
            expires = int(query_dict['expires'][0])
        except (KeyError, ValueError):
            return False

        signer = Signer()
        full_value = '{}-{}'.format(parsed_url.path, expires)
        try:
            signer.unsign('{}{}{}'.format(full_value, signer.sep, signature))
        except BadSignature:
            return False
        return expires > timezone.now().timestamp()

    def get_downloadable_url(self):
        # Override this
        return

    def get_downloadable_signed_url(self, hours=1):
        if not self.downloadable or not self.downloadable.source:
            return None
        url = self.get_downloadable_url()
        expires = int(timezone.now().timestamp() + hours * 3600)
        signer = Signer()
        full_value = '{}-{}'.format(url, expires)
        full_signature = signer.sign(full_value)
        signature = full_signature.split(signer.sep)[-1]  # just the signature part
        return '{}?{}'.format(
            url, urllib.parse.urlencode({'signature': signature, 'expires': expires})
        )


class SpamDetectMixin:
    spam_detect_field_names = ['title', 'content']
    extractor = URLExtract()

    @staticmethod
    def _has_spam_words_in_field(field_content):
        if not field_content:
            return False
        for w in SpamWord.objects.all():
            if w.word.lower() in field_content.lower():
                return True
        return False

    def _has_disallowed_links_in_field(self, field_content):
        if not field_content:
            return False
        # Find all the URL in the text
        found_urls = self.extractor.find_urls(field_content)
        if not found_urls:
            return False
        allowed_domains = AllowedDomain.objects.all()
        if not allowed_domains:
            return False
        # For every URL, check if it contains any of the allowed domains.
        # At the first URL that does not contain an allowed domain, stop and return False.
        for url in found_urls:
            allowed_domain_found = False
            for allowed_domain in allowed_domains:
                if allowed_domain.url in url:
                    allowed_domain_found = True
            if not allowed_domain_found:
                return True
        # If we made it here, all links found are valid.
        return False

    def _field_has_spam(self, field_name):
        f = getattr(self, field_name)
        if self._has_spam_words_in_field(f):
            return True
        if self._has_disallowed_links_in_field(f):
            return True
        return False

    @property
    def has_spam(self):
        for f in self.spam_detect_field_names:
            if self._field_has_spam(f):
                return True
        return False
