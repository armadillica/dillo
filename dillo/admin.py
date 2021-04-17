import logging
from django import forms
from django.conf import settings
from django.contrib import admin
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

log = logging.getLogger(__name__)


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
    actions = ['process_videos']
    autocomplete_fields = ['media']
    list_display = ('__str__', 'show_link', 'hash_id', 'status', 'created_at', 'updated_at')
    list_display_links = ('__str__',)
    readonly_fields = ('hash_id', 'tags', 'created_at', 'updated_at', 'user')

    def show_link(self, obj):
        return mark_safe('<a href="%s" target="_blank">View</a>' % obj.get_absolute_url())

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


@admin.register(dillo.models.events.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'visibility', 'show_link')
    exclude = ('image_height', 'image_width', 'attendees')
    prepopulated_fields = {'slug': ('name',)}

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
    readonly_fields = ('created_at', 'updated_at', 'user', 'bookmarks')
    can_delete = False
    exclude = (
        'header_height',
        'header_width',
        'avatar_height',
        'avatar_width',
        'reel_thumbnail_16_9_height',
        'reel_thumbnail_16_9_width',
    )
    inlines = [ProfileLinksInline, ProfileBadgesInline]


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

    fieldsets = (
        (None, {'fields': ('email', 'password',)}),
        (
            _('Permissions'),
            {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
                'classes': ('collapse',),
            },
        ),
        (
            _('Important dates'),
            {'fields': ('date_joined', 'last_login'), 'classes': ('collapse',),},
        ),
    )

    list_display = (
        'username',
        'get_name',
        'email',
        'get_is_verified',
        'last_login',
        'get_likes_count',
        'get_posts_count',
    )
    readonly_fields = ('first_name', 'last_name')
    list_filter = ('is_superuser', 'is_active', EmailIsVerifiedListFilter)
    ordering = ('-last_login',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_posts_count=Count("post", distinct=True),)
        return queryset

    def get_name(self, instance: User):
        return instance.profile.name

    def get_is_verified(self, instance: User):
        return instance.profile.is_verified

    def get_likes_count(self, instance: User):
        return instance.profile.likes_count

    def get_posts_count(self, instance: User):
        return instance.post_set.all().count()

    get_name.short_description = 'Name'
    get_is_verified.short_description = 'Is Verified'
    get_is_verified.boolean = True
    get_likes_count.short_description = 'Likes Count'
    get_likes_count.admin_order_field = 'profile__likes_count'
    get_posts_count.short_description = 'Posts Count'
    get_posts_count.admin_order_field = '_posts_count'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(dillo.models.comments.Comment)


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
        (None, {'fields': ['id', 'source', 'source_filename', 'source_type', 'thumbnail',],},),
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
