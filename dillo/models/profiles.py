import logging
import urllib.parse

from actstream.models import followers, following, Follow
from actstream import action
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from django.utils import timezone

from taggit.managers import TaggableManager
from django_countries.fields import CountryField

import dillo.tasks.profile
from dillo.models.communities import Community
from dillo.models.mixins import (
    CreatedUpdatedMixin,
    get_upload_to_hashed_path,
    ChangeAwareness,
    SocialLink,
)
from dillo.validators import validate_reel_url

log = logging.getLogger(__name__)


class City(models.Model):
    """Cities of the world.

    Populated in migration 0006.
    """

    name = models.CharField(max_length=256)
    name_ascii = models.CharField(max_length=256)
    lat = models.FloatField(verbose_name='latitude')
    lng = models.FloatField(verbose_name='longitude')
    country = models.CharField(max_length=2)

    def __str__(self):
        return self.name


class TrustLevel(models.IntegerChoices):
    """Currently only used to trigger spam detection or not."""

    NEW = 0, 'New User'
    BASIC = 1, 'Basic User'
    MEMBER = 2, 'Member'
    REGULAR = 3, 'Regular'
    LEADER = 4, 'Leader'


class Profile(ChangeAwareness, CreatedUpdatedMixin, models.Model):
    """Public profile of a User.

    This information is displayed in the public profile page.
    """

    SETUP_STAGES = (
        ('avatar', 'Avatar'),
        ('bio', 'Bio'),
        ('links', 'links'),
        ('tags', 'Tags'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    name = models.CharField(max_length=125)
    tagline = models.CharField(
        max_length=80, blank=True, help_text='Tell us about you. In 80 characters.'
    )
    bio = models.TextField(max_length=512, blank=True, help_text='Your life story.')
    website = models.URLField(blank=True, help_text='Your main website.')
    location = models.CharField(
        max_length=255, blank=True, help_text='Your place in the world. Usually "City, Country"'
    )
    city = models.CharField(max_length=256, blank=True, null=True)
    city_ref = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name='profiles', null=True, blank=True
    )
    country = CountryField(null=True, blank=True)
    reel = models.URLField(
        blank=True,
        validators=[validate_reel_url],
        help_text="A YouTube or Vimeo link to your demo reel.",
    )

    avatar = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='avatar_height',
        width_field='avatar_width',
    )
    avatar_height = models.PositiveIntegerField(null=True)
    avatar_width = models.PositiveIntegerField(null=True)

    # Thumbnail used to preview the profile's reel in the reel gallery.
    reel_thumbnail_16_9 = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='reel_thumbnail_16_9_height',
        width_field='reel_thumbnail_16_9_width',
    )
    reel_thumbnail_16_9_height = models.PositiveIntegerField(null=True)
    reel_thumbnail_16_9_width = models.PositiveIntegerField(null=True)

    is_setup_complete = models.BooleanField(default=False)
    # Which page should be displayed to the user after they sign up,
    # unless their user.profile.is_setup_complete = True.
    # Possible stages:
    # - avatar
    # - bio
    # - links
    # - tags
    setup_stage = models.CharField(
        choices=SETUP_STAGES, max_length=10, default='avatar', blank=True
    )

    # Cache-like field, that is updated whenever a post owned by the
    # user is liked or unliked. The update is done via signals.
    likes_count = models.PositiveIntegerField(default=0)

    # Amount of profile views (visits to /<username>. This value
    # is atomically incremented based on the ITEM_HITS_FACTOR
    views_count = models.PositiveIntegerField(default=0)

    ip_address = models.GenericIPAddressField(blank=True, null=True)

    is_looking_for_work = models.BooleanField(
        default=False,
        verbose_name='Looking for work',
        help_text='Your profile will show that you are open to work opporunities.',
    )

    # Posts that have been added by the user to the "Bookmarks" list
    bookmarks = models.ManyToManyField('Post', related_name='bookmarks')

    # Badges assigned through signals and other activities
    badges = models.ManyToManyField('Badge', related_name='badges', blank=True)

    # Trust levels are used for content moderation
    trust_level = models.IntegerField(choices=TrustLevel.choices, default=TrustLevel.NEW)

    tags = TaggableManager(blank=True)

    @property
    def followers_count(self):
        return len(followers(self.user))

    @property
    def following_count(self):
        """The Users that a user is following."""
        return len(following(self.user, User))

    @property
    def next_events_attending(self):
        """The closest public events that a user will attend in the future."""
        return (
            self.user.events.filter(starts_at__gt=timezone.now(), visibility='public')
            .order_by('starts_at')
            .all()
        )

    @property
    def website_hostname(self):
        """Given a website url, return the hostname only.

        This useful for showing a url in the frontend. For example:
        https://blender.org -> blender.org
        """
        if not self.website:
            return
        url = urllib.parse.urlparse(self.website)
        hostname = url.hostname.replace("www.", "")
        return hostname

    def get_absolute_url(self):
        return reverse('profile-detail', kwargs={'username': self.user.username})

    @property
    def absolute_url(self) -> str:
        return 'http://%s%s' % (Site.objects.get_current().domain, self.get_absolute_url())

    @property
    def is_verified(self) -> bool:
        """Check if at least one of the emails was verified."""
        return self.user.emailaddress_set.filter(verified=True).count() > 0

    def recalculate_likes(self):
        """Reconciles likes count, from liked posts."""
        likes_count = 0
        for post in self.user.post_set.all():
            likes_count += post.likes.count()
        self.likes_count = likes_count
        self.save()

    @property
    def first_name_guess(self):
        """Take the first word of the 'name' attribute and return it."""
        if not self.name:
            return None
        return self.name.split(' ')[0]

    @property
    def followed_communities(self):
        follows = Follow.objects.filter(
            content_type=ContentType.objects.get_for_model(Community), user=self.user
        )
        return [c.follow_object for c in follows]

    @property
    def serialized_badges(self):
        badges = []
        for badge in self.badges.all():
            badges.append({'name': badge.name, 'slug': badge.slug, 'urlImage': badge.image.url})
        return badges

    @property
    def location_label(self):
        if self.city and self.country:
            return f"{self.city}, {self.country.name}"
        elif self.country:
            return self.country.name
        else:
            return ''

    def save(self, *args, **kwargs):
        """Extend save() with reel thumbnail fetching.

        If reel is set, fetch thumbnail_url via micawber and set it as reel_thumbnail.
        """
        # Look up city in the City table and try to associate it
        self.city_ref = City.objects.filter(name__iexact=self.city).first()

        super().save(*args, **kwargs)

        if self.reel == '':
            log.debug('Skipping thumbnail fetch for reel of profile %i' % self.user_id)
            return
        if self.data_changed(['reel']):
            log.debug('Updating reel thumbnail for user %i' % self.user_id)
            dillo.tasks.profile.update_profile_reel_thumbnail(self.user_id)
            # Create activity for reel update
            action.send(self.user, verb='updated their reel', action_object=self)

        if self.data_changed(['name']):
            log.debug('Updating newsletter information for user')
            dillo.tasks.profile.update_mailing_list_subscription(self.user.email)

    def __str__(self):
        return self.name or self.user.username


class ProfileLinks(SocialLink):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='links')


class EmailNotificationsSettings(ChangeAwareness, models.Model):
    """User settings for email notifications.

    By default, email notifications for activities such as likes,
    mentions or comments are enabled.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='email_notifications_settings'
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name='Email Notifications',
        help_text='Enable if you want to receive emails about comments to your content or replies '
        'to your comments.',
    )
    is_enabled_for_like = models.BooleanField(
        default=True,
        verbose_name='Email on received likes',
        help_text='Enable if you want to receive emails about likes on your comments or posts.',
    )
    is_enabled_for_follow = models.BooleanField(
        default=True,
        verbose_name='Email on profile follow',
        help_text='Enable if you want to receive emails when someone follows your profile.',
    )
    is_enabled_for_comment = models.BooleanField(
        default=True,
        verbose_name='Email on comments',
        help_text='Enable if you want to receive emails when someone comments on your content.',
    )
    is_enabled_for_reply = models.BooleanField(
        default=True,
        verbose_name='Email on replies to your comments',
        help_text='Enable if you want to receive emails when someone leaves a response to your '
        'comments.',
    )
    is_enabled_for_newsletter = models.BooleanField(
        default=False,
        verbose_name='Receive hand-crafted newsletter.',
        help_text='Enable if you want to receive updates about the platform and the community. '
        'Follow the journey with us!',
    )

    def __str__(self):
        return 'Email Notification Setting for %s' % self.user

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update mailing list subscription status.
        if self.data_changed(['is_enabled_for_newsletter']):
            log.debug("Updating mailing list subscription settings")
            dillo.tasks.profile.update_mailing_list_subscription(
                self.user.email, self.is_enabled_for_newsletter
            )


class Badge(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    description = models.TextField()
    image = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='image_height',
        width_field='image_width',
    )
    image_height = models.PositiveIntegerField(null=True)
    image_width = models.PositiveIntegerField(null=True)

    def __str__(self):
        return self.name
