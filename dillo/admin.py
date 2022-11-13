import logging
from typing import List, Tuple, Any

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ChangeList
from django.db.models.query import QuerySet
from django.utils.encoding import force_str
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.db.models import Count
from django.http import HttpResponseServerError
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.translation import gettext as _
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from tinymce.widgets import TinyMCE

import dillo.models.comments
import dillo.models.events
import dillo.models.posts
import dillo.models.profiles
import dillo.models.newsletter
import dillo.models.communities
import dillo.models.software
import dillo.models.static_assets
import dillo.models.jobs
import dillo.models.moderation

from dillo.moderation import deactivate_user_and_remove_content

log = logging.getLogger(__name__)


class PreFilteredListFilter(SimpleListFilter):
    """Reusable admin filtering.

    Via Greg and JohnGalt on SO.
    """

    # Either set this or override .get_default_value()
    default_value = None

    no_filter_value = 'all'
    no_filter_name = _("All")

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = None

    # Parameter for the filter that will be used in the URL query.
    parameter_name = None

    def get_default_value(self):
        if self.default_value is not None:
            return self.default_value
        raise NotImplementedError(
            'Either the .default_value attribute needs to be set or '
            'the .get_default_value() method must be overridden to '
            'return a URL query argument for parameter_name.'
        )

    def get_lookups(self) -> List[Tuple[Any, str]]:
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        raise NotImplementedError(
            'The .get_lookups() method must be overridden to '
            'return a list of tuples (value, verbose value).'
        )

    # Overriding parent class:
    def lookups(self, request, model_admin) -> List[Tuple[Any, str]]:
        return [(self.no_filter_value, self.no_filter_name)] + self.get_lookups()

    # Overriding parent class:
    def queryset(self, request, queryset: QuerySet) -> QuerySet:
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() is None:
            return self.get_default_queryset(queryset)
        if self.value() == self.no_filter_value:
            return queryset.all()
        return self.get_filtered_queryset(queryset)

    def get_default_queryset(self, queryset: QuerySet) -> QuerySet:
        return queryset.filter(**{self.parameter_name: self.get_default_value()})

    def get_filtered_queryset(self, queryset: QuerySet) -> QuerySet:
        try:
            return queryset.filter(**self.used_parameters)
        except (ValueError, ValidationError) as e:
            # Fields may raise a ValueError or ValidationError when converting
            # the parameters to the correct type.
            raise IncorrectLookupParameters(e)

    # Overriding parent class:
    def choices(self, changelist: ChangeList):
        """
        Overridden to prevent the default "All".
        """
        value = self.value() or force_str(self.get_default_value())
        for lookup, title in self.lookup_choices:
            yield {
                'selected': value == force_str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }


class CommunityCategoryInline(admin.TabularInline):
    """Inline form for Categories.

    This gets included in CommunityAdmin.
    """

    model = dillo.models.communities.CommunityCategory
    fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class CommunityLinkInline(admin.TabularInline):
    """Inline form for Community Links.

    This gets included in CommunityAdmin.
    """

    model = dillo.models.communities.CommunityLink
    fields = ['url']


@admin.register(dillo.models.communities.Community)
class CommunityAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    fields = [
        'name',
        'slug',
        'tagline',
        'description',
        'visibility',
        'is_featured',
        'thumbnail',
        'logo',
        'header',
        'theme_color',
    ]
    inlines = [CommunityCategoryInline, CommunityLinkInline]

    list_display = ('name', 'is_featured', 'show_link')

    def show_link(self, obj):
        return mark_safe('<a href="%s" target="_blank">View</a>' % obj.get_absolute_url())


@admin.register(dillo.models.posts.Post)
class PostAdmin(admin.ModelAdmin):
    actions = ['process_videos', 'approve_posts']
    list_per_page = 50
    list_display = (
        '__str__',
        'user',
        'community',
        'show_link',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('community', 'is_pinned_by_moderator', 'is_link', 'status', 'visibility')
    list_display_links = ('__str__',)
    search_fields = ('content', 'title', 'user__username')
    autocomplete_fields = ['media']
    readonly_fields = ('hash_id', 'tags', 'created_at', 'updated_at', 'user')

    def show_link(self, obj):
        return mark_safe(f'<a href="{obj.get_absolute_url()}" target="_blank">{obj.hash_id}</a>')

    def process_videos(self, request, queryset):
        videos_processing = 0
        # For each post, process all videos attached if available
        for a in queryset:
            videos_processing += a.process_videos()
        rows_updated = videos_processing
        if videos_processing == 0:
            message_bit = "No video is"
        elif videos_processing == 1:
            message_bit = "1 video is"
        else:
            message_bit = "%s videos are" % rows_updated
        self.message_user(request, "%s processing." % message_bit)

    process_videos.short_description = "Process videos for selected posts"

    def approve_posts(self, request, queryset):
        """Publish posts with a 'review' status"""
        published_posts = 0
        processing_posts = 0
        for p in queryset:
            if p.status != 'review':
                continue
            p.process_videos()
            if p.may_i_publish:
                p.publish()
                published_posts += 1
            else:
                processing_posts += 1

        message = ''
        if published_posts:
            message += f"{published_posts} post(s) published"
        if published_posts and processing_posts:
            message += " and "
        if processing_posts:
            message += f"{processing_posts} post(s) processing."

        if message == '':
            message = 'No post needed review.'

        self.message_user(request, message)

    approve_posts.short_description = "Approve selected posts"


@admin.register(dillo.models.events.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'visibility', 'show_link')
    exclude = ('attendees',)
    prepopulated_fields = {'slug': ('name',)}

    def show_link(self, obj):
        return mark_safe('<a href="%s" target="_blank">View</a>' % obj.get_absolute_url())


@admin.register(dillo.models.jobs.Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'visibility', 'show_link')
    autocomplete_fields = ['user']
    exclude = ('image_height', 'image_width')
    readonly_fields = ('created_at', 'updated_at')

    def show_link(self, obj):
        return mark_safe('<a href="%s" target="_blank">View</a>' % obj.get_absolute_url())


@admin.register(dillo.models.newsletter.Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    actions = ['send']
    change_form_template = 'admin/newsletter_changeform.html'


def send_newsletter(request, newsletter_id):
    """Custom view to preview and send a newsletter."""
    newsletter = get_object_or_404(dillo.models.newsletter.Newsletter, id=newsletter_id)
    if request.method == "GET":
        return render(
            request,
            'admin/newsletter_send.html',
            {
                'newsletter': newsletter,
                'newsletter_address': settings.MAILING_LIST_NEWSLETTER_EMAIL,
            },
        )
    elif request.method == "POST":
        recipients = request.POST.get('recipients')
        if not recipients or recipients not in {'mass', 'preview'}:
            return HttpResponseServerError()
        if recipients == 'preview':
            newsletter.send(is_preview=True)
        else:
            newsletter.send(is_preview=False)
        return redirect('admin:dillo_newsletter_changelist')


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


admin.site.register(dillo.models.software.Software)


class EmailIsVerifiedListFilter(admin.SimpleListFilter):
    """Filter to display verified/non verified accounts."""

    title = 'is verified'
    parameter_name = 'is_verified'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Yes'),
            ('No', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(emailaddress__verified=True)
        if self.value() == 'No':
            return queryset.filter(emailaddress__verified=False)


class ProfileLinksInline(admin.TabularInline):
    """Inline form for Profile Links.

    This gets included in ProfileAdmin.
    """

    model = dillo.models.profiles.ProfileLinks


class ProfileBadgesInline(admin.TabularInline):
    model = dillo.models.profiles.Badge


class ProfileInline(admin.StackedInline):
    model = dillo.models.profiles.Profile
    readonly_fields = ('created_at', 'updated_at', 'user', 'bookmarks', 'city_ref')
    can_delete = False
    exclude = (
        'header_height',
        'header_width',
        'avatar_height',
        'avatar_width',
        'reel_thumbnail_16_9_height',
        'reel_thumbnail_16_9_width',
    )
    # autocomplete_fields = [
    #     'city_ref',
    # ]

    inlines = [ProfileLinksInline, ProfileBadgesInline]


class IsActiveFilter(PreFilteredListFilter):
    default_value = '1'
    title = _('is active')
    parameter_name = 'is_active'

    def get_lookups(self):
        return [
            ('1', 'Yes'),
            ('0', 'No'),
        ]


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'email',
                    'password',
                )
            },
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
                'classes': ('collapse',),
            },
        ),
        (
            _('Important dates'),
            {
                'fields': (
                    'date_joined',
                    'last_login',
                ),
                'classes': ('collapse',),
            },
        ),
    )

    list_display = (
        'username',
        'get_name',
        'email',
        'is_active',
        'get_bio',
        'get_trust_level',
        'get_website',
        'get_likes_count',
        'get_posts_count',
        'get_ip_address',
        'date_joined',
        'last_login',
    )
    readonly_fields = ('first_name', 'last_name')
    list_filter = ('is_superuser', IsActiveFilter, EmailIsVerifiedListFilter)
    ordering = ('-date_joined',)
    actions = ['deactivate_users_and_remove_content', 'make_member']
    search_fields = [
        'id',
        'username',
        'email',
        'profile__name',
        'profile__bio',
        'profile__website',
    ]

    def deactivate_users_and_remove_content(self, request, queryset):
        deactivated_users = 0
        # For each post, process all videos attached if available
        for u in queryset:
            deactivate_user_and_remove_content(u)
            deactivated_users += 1
        rows_updated = deactivated_users
        if deactivated_users == 0:
            message_bit = "No user was"
        elif deactivated_users == 1:
            message_bit = "1 user was"
        else:
            message_bit = "%s user were" % rows_updated
        self.message_user(request, "%s deactivated." % message_bit)

    deactivate_users_and_remove_content.short_description = "Deactivate and remove content"

    @admin.action(description='Make member')
    def make_member(self, request, queryset):
        for u in queryset:
            u.profile.trust_level = dillo.models.profiles.TrustLevel.MEMBER
            u.profile.save()
        self.message_user(request, "Set 'member' status.")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _posts_count=Count("post", distinct=True),
        )
        return queryset

    def get_name(self, instance: User):
        return instance.profile.name

    def get_likes_count(self, instance: User):
        return instance.profile.likes_count

    def get_posts_count(self, instance: User):
        return instance.post_set.all().count()

    def get_website(self, instance: User):
        return mark_safe('<a href="{0}" target="_blank">{0}</a>'.format(instance.profile.website))

    def get_bio(self, instance: User):
        return instance.profile.bio[:80]

    def get_ip_address(self, instance: User):
        ip_address = instance.profile.ip_address
        if ip_address:
            url = 'https://iplocation.io/ip/'
            return mark_safe(f'<a href="{url}{ip_address}" target="_blank">{ip_address}</a>')
        else:
            return '-'

    get_name.short_description = 'Name'
    get_website.short_description = 'Website'
    get_bio.short_description = 'Bio'
    get_ip_address.short_description = 'IP Address'
    get_likes_count.short_description = 'Likes'
    get_likes_count.admin_order_field = 'profile__likes_count'
    get_posts_count.short_description = 'Posts'
    get_posts_count.admin_order_field = '_posts_count'

    @admin.display(ordering='profile__trust_level', description='Trust level')
    def get_trust_level(self, obj):
        return obj.profile.trust_level


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(dillo.models.comments.Comment)
class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ['user']
    list_display = ['id', 'get_content', 'user', 'created_at', 'show_link']
    readonly_fields = ('entity_content_type', 'parent_comment', 'tags')
    search_fields = ('content', 'user__username')

    def show_link(self, obj):
        return mark_safe('<a href="%s" target="_blank">View</a>' % obj.get_absolute_url())

    def get_content(self, obj):
        return obj.content[:100]

    get_content.short_description = "description"


class TinyMCEFlatPageAdmin(FlatPageAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'content':
            return db_field.formfield(
                widget=TinyMCE(
                    attrs={'cols': 80, 'rows': 30},
                    mce_attrs={'external_link_list_url': reverse('tinymce-linklist')},
                )
            )
        return super(TinyMCEFlatPageAdmin, self).formfield_for_dbfield(db_field, **kwargs)


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, TinyMCEFlatPageAdmin)


class StaticAssetVideoInline(admin.TabularInline):
    """Inline form for Video."""

    model = dillo.models.static_assets.Video


@admin.register(dillo.models.static_assets.StaticAsset)
class StaticAssetAdmin(admin.ModelAdmin):
    inlines = [StaticAssetVideoInline]
    list_display = [
        '__str__',
    ]
    fieldsets = (
        (
            None,
            {
                'fields': [
                    'id',
                    'source',
                    'source_filename',
                    'source_type',
                    'thumbnail',
                ],
            },
        ),
        (
            'If you are uploading an image or a video',
            {
                'fields': (),
                'description': 'The fields below depend on the source type of the uploaded '
                'asset. Add an <strong>Image</strong> if you are uploading an '
                'image, or a <strong>Video</strong> for video uploads.',
            },
        ),
    )
    list_filter = [
        'source_type',
    ]
    search_fields = [
        'source',
        'source_filename',
        'source_type',
    ]
    readonly_fields = ['source_filename', 'id']


@admin.register(dillo.models.profiles.Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview')
    exclude = ('image_height', 'image_width')
    prepopulated_fields = {'slug': ('name',)}

    def image_preview(self, obj):
        if not obj.image:
            return
        return format_html(
            '<img src="{0}" style="width: 20px; height:20px;" />'.format(obj.image.url)
        )


@admin.register(dillo.models.moderation.SpamWord)
class SpamWordAdmin(admin.ModelAdmin):
    pass


@admin.register(dillo.models.moderation.AllowedDomain)
class AllowedDomainAdmin(admin.ModelAdmin):
    pass
