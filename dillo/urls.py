from django.conf import settings
from django.contrib.flatpages.views import flatpage
from django.urls import path, include
from django.views.generic import TemplateView

import dillo.views.comments
import dillo.views.contact
import dillo.views.custom_logout
import dillo.views.events
import dillo.views.likes
import dillo.views.mixins
import dillo.views.posts
import dillo.views.posts.publish
import dillo.views.posts.queries
import dillo.views.posts.videos
import dillo.views.report
import dillo.views.users.account
import dillo.views.users.bookmarks
import dillo.views.users.homepage
import dillo.views.users.notifications
import dillo.views.users.profile
import dillo.views.theater
import dillo.views.jobs
import dillo.views.emails

# User Pages
urlpatterns = [
    # XXX - Temporary change to show PostListView (aka /explore) as homepage for users.
    # path('', dillo.views.users.homepage.HomepageView.as_view(), name='homepage'),
    path('', dillo.views.mixins.PostListView.as_view(), name='homepage'),
    path(
        'logout/', dillo.views.custom_logout.CustomLogoutView.as_view(next_page='/'), name='logout'
    ),
    # Embedded list view
    path(
        'e/stream/',
        dillo.views.users.homepage.PostsStreamUserListEmbedView.as_view(),
        name='embed_stream',
    ),
]

# User Account
urlpatterns += [
    path('a/delete', dillo.views.users.account.AccountDelete.as_view(), name='account_delete'),
    path(
        'a/delete/success',
        TemplateView.as_view(template_name='dillo/account_delete_success.pug'),
        name='account_delete_success',
    ),
    path(
        'a/update-username',
        dillo.views.users.account.AccountUpdateUsername.as_view(),
        name='account_update_username',
    ),
    path(
        'a/update-username/success',
        TemplateView.as_view(template_name='dillo/account_update_username_success.pug'),
        name='account_update_username_success',
    ),
    path(
        'accounts/profile/',
        dillo.views.users.profile.ProfileUpdateView.as_view(),
        name='profile_edit',
    ),
    path(
        'accounts/settings/',
        dillo.views.users.account.AccountSettings.as_view(),
        name='account_settings',
    ),
]

# Rigs
urlpatterns += [
    path('rigs/', include('rigs.urls')),
]

# Posts
urlpatterns += [
    # Explore list view
    path('explore/', dillo.views.mixins.PostListView.as_view(), name='explore'),
    # Embedded list view
    path('e/explore/', dillo.views.mixins.PostListEmbedView.as_view(), name='embed_posts_list'),
    # Explore tags view
    path(
        'explore/tags/<str:tag_name>',
        dillo.views.posts.queries.PostByTagsListView.as_view(),
        name='posts_list_tag',
    ),
    # Embedded tags list
    path(
        'e/explore/tags/<str:tag_name>',
        dillo.views.posts.queries.PostsByTagListEmbedView.as_view(),
        name='embed_posts_list_tag',
    ),
    # Post URLs
    path('p/create/', dillo.views.posts.publish.PostCreateView.as_view(), name='post_create'),
    path('p/<slug:hash_id>', dillo.views.posts.PostDetailView.as_view(), name='post_detail'),
    path('p/<slug:hash_id>/delete', dillo.views.posts.post_delete, name='post_delete'),
    path('p/<slug:hash_id>/status', dillo.views.posts.publish.post_status, name='post_status'),
    path(
        'p/<slug:hash_id>/upload',
        dillo.views.posts.publish.post_file_upload,
        name='post_file_upload',
    ),
    path(
        'p/<slug:hash_id>/unpublished-uploads',
        dillo.views.posts.publish.post_get_unpublished_uploads,
        name='post_unpublished_uploads',
    ),
    path(
        'p/<slug:hash_id>/delete-unpublished-upload',
        dillo.views.posts.publish.delete_unpublished_upload,
        name='delete_unpublished_upload',
    ),
    path(
        'p/<slug:hash_id>/comments/',
        dillo.views.comments.CommentsListView.as_view(),
        name='comments_list',
    ),
    # Post update
    path(
        'e/<slug:hash_id>/update',
        dillo.views.posts.PostUpdateView.as_view(),
        name='embed_post_update',
    ),
    path(
        'e/<slug:hash_id>/update/success',
        dillo.views.posts.PostUpdateSuccessEmbedView.as_view(),
        name='post_update_success_embed',
    ),
    # Video Processing webhook
    path(
        'p/<slug:hash_id>/video/<int:video_id>',
        dillo.views.posts.publish.post_update_video_processing,
        name='post_update_video_processing',
    ),
    # Likes
    path(
        'l/<int:content_type_id>/<int:object_id>', dillo.views.likes.like_toggle, name='like_toggle'
    ),
    path(
        'e/likes/<int:content_type_id>/<int:object_id>',
        dillo.views.likes.LikesListEmbed.as_view(),
        name='embed_likes_list',
    ),
    # Video stats
    path(
        'v/<int:video_id>',
        dillo.views.posts.videos.VideoViewsCountIncreaseView.as_view(),
        name='video_views_count_increase',
    ),
    path('activity/', include('actstream.urls')),
]

# Comments
urlpatterns += [
    path('c/create/', dillo.views.comments.comment_create, name='comment_create'),
    path('c/<int:comment_id>/delete/', dillo.views.comments.comment_delete, name='comment_delete'),
]

# Content Reporting
urlpatterns += [
    path(
        'e/report/<int:content_type_id>/<int:object_id>',
        dillo.views.report.ReportContentView.as_view(),
        name='report_content',
    ),
    path(
        'e/report/confirm',
        TemplateView.as_view(template_name='dillo/report_content_success_embed.pug'),
        name='report_content_success_embed',
    ),
]

# Contact and Feedback
urlpatterns += [
    path('e/contact/', dillo.views.contact.ContactView.as_view(), name='contact'),
    path(
        'e/contact/confirm',
        TemplateView.as_view(template_name='dillo/contact_success_embed.pug'),
        name='contact-success',
    ),
]

# Bookmarks
urlpatterns += [
    path('bookmarks/', dillo.views.users.bookmarks.BookmarksView.as_view(), name='bookmarks'),
    path(
        'e/bookmarks/',
        dillo.views.users.bookmarks.BookmarksEmbedView.as_view(),
        name='embed_bookmarks',
    ),
    # Bookmark post
    path(
        'b/<int:post_id>',
        dillo.views.users.bookmarks.BookmarkPostView.as_view(),
        name='bookmark_toggle',
    ),
]

# Events
urlpatterns += [
    path('events', dillo.views.events.EventListView.as_view(), name='event_list'),
    path('events/<slug:slug>/', dillo.views.events.EventDetailView.as_view(), name='event_detail'),
    path(
        'events/<slug:slug>/<str:toggle_action>',
        dillo.views.events.EventAttendToggle.as_view(),
        name='event_attend_toggle',
    ),  # toggle_action can be 'attend' or 'decline'
]

# Search
urlpatterns += [
    # Explore tags view
    path('search', dillo.views.posts.queries.PostSearchListView.as_view(), name='posts_search'),
    # Embedded tags list
    path(
        'e/search',
        dillo.views.posts.queries.PostsSearchEmbedView.as_view(),
        name='embed_posts_search',
    ),
]

# Theater
urlpatterns += [
    path('theater/reels/', dillo.views.theater.ReelListView.as_view(), name='reel-list'),
    path(
        'theater/reels/<int:profile_id>',
        dillo.views.theater.ReelDetailView.as_view(),
        name='reel-detail',
    ),
    path('theater/shorts/', dillo.views.theater.ShortListView.as_view(), name='short-list'),
    path(
        'theater/shorts/<int:pk>',
        dillo.views.theater.ShortDetailView.as_view(),
        name='short-detail',
    ),
    path(
        'theater/shorts/submit', dillo.views.theater.ShortCreateView.as_view(), name='short-create'
    ),
    path(
        'theater/shorts/<int:pk>/update',
        dillo.views.theater.ShortUpdateView.as_view(),
        name='short-update',
    ),
]

# Jobs
urlpatterns += [
    path('jobs/', dillo.views.jobs.JobListView.as_view(), name='job-list'),
    path('jobs/<int:pk>', dillo.views.jobs.JobDetailView.as_view(), name='job-detail'),
    path('jobs/submit', dillo.views.jobs.JobCreateView.as_view(), name='job-create'),
    path('jobs/<int:pk>/update', dillo.views.jobs.JobUpdateView.as_view(), name='job-update'),
]

# Flat Pages
urlpatterns += [
    path('about/', flatpage, {'url': '/about/'}, name='about'),
    path('blog/', flatpage, {'url': '/blog/'}, name='blog'),
    path('terms/', flatpage, {'url': '/terms/'}, name='terms'),
    path('privacy/', flatpage, {'url': '/privacy/'}, name='privacy'),
]

# TinyMCE
urlpatterns += [
    path('tinymce/', include('tinymce.urls')),
]

# Feeds
urlpatterns += [
    path(
        'feed/notifications/',
        dillo.views.users.notifications.FeedNotificationsView.as_view(),
        name='notifications',
    ),
    path(
        'feed/notifications/mark-as-read',
        dillo.views.users.notifications.NotificationsMarkAsReadView.as_view(),
        name='notifications-mark-as-read',
    ),
    path(
        'accounts/notifications',
        dillo.views.users.account.AccountEmailNotificationsView.as_view(),
        name='account-email-notifications',
    ),
]


# Mailgun webhook for mailing list unsubscribes
urlpatterns += [
    path(
        'w/newsletter-unsubscribe',
        dillo.views.emails.webhook_newlsetter_unsubscribe,
        name='webhook-newsletter-unsubscribe',
    ),
]


if settings.DEBUG:
    # Video upload for debug
    urlpatterns += [
        path(
            'debug-video-transfer/<path:video_path>',
            dillo.views.posts.publish.debug_video_transfer,
            name='debug_video_transfer',
        )
    ]

    # Email template previews
    urlpatterns += [
        path(
            'preview-email-templates/',
            dillo.views.emails.preview_email_list,
            name='preview_email_template_list',
        ),
        path(
            'preview-email-templates/<str:email_template>',
            dillo.views.emails.preview_email_detail,
            name='preview_email_template_detail',
        ),
        path(
            'preview-email-templates-send/<str:email_template>',
            dillo.views.emails.preview_email_send,
            name='preview_email_template_send',
        ),
    ]

    # Design System
    urlpatterns += [
        path(
            'design-system/',
            TemplateView.as_view(template_name='dillo/design_system.pug'),
            name='design-system',
        ),
    ]

# User Profile (keep at the end, since "Profile URL" catches all urls
urlpatterns += [
    # Profile setup
    path('profile/setup/', dillo.views.users.profile.ProfileSetup.as_view(), name='profile_setup'),
    # Profile URL
    path(
        '<username>/', dillo.views.users.profile.ProfileDetailView.as_view(), name='profile_details'
    ),
    # User followers
    path(
        'e/followers/<int:user_id>',
        dillo.views.users.profile.UserFollowersListEmbed.as_view(),
        name='embed_user_followers_list',
    ),
    # User following
    path(
        'e/following/<int:user_id>',
        dillo.views.users.profile.UserFollowingListEmbed.as_view(),
        name='embed_user_following_list',
    ),
    # Posts by user
    path(
        'a/<int:user_id>/',
        dillo.views.users.profile.PostsByUserListView.as_view(),
        name='posts_by_user_list',
    ),
]
