from django.conf import settings
import sorl.thumbnail

from dillo.models.feeds import FeedEntry
from dillo.views.mixins import OgData
from dillo.models.communities import Community


def notifications_count(request):
    """Count the unread notifications for the authenticated user."""
    if 'user' not in request or request.user.is_anonymous:
        count = 0
    else:
        count = FeedEntry.objects.filter(
            user=request.user, is_read=False, category='notification',
        ).count()
    return {
        'notifications_count': count,
    }


def google_analytics_tracking_id(_):
    return {'GOOGLE_ANALYTICS_TRACKING_ID': settings.GOOGLE_ANALYTICS_TRACKING_ID}


def media_uploads_accepted_mimes(_):
    return {'MEDIA_UPLOADS_ACCEPTED_MIMES': list(settings.MEDIA_UPLOADS_ACCEPTED_MIMES)}


def communities_featured(_):
    return {'communities_featured': Community.objects.filter(is_featured=True)}


def default_og_data(_):
    """Default values for the Open Graph data.

    This is used as fallback for populating the og: and twitter: tags in every page.
    """
    return {
        'og_data_default': OgData(
            title='anima.to',
            description='Connecting animators frame by frame.',
            image_field=None,
            image_alt='anima.to',
        )
    }


def current_user_js(request):
    current_user = {
        'isAuthenticated': request.user.is_authenticated,
        'username': (None if not request.user.is_authenticated else request.user.username),
        'avatar': None,
        'url': (None if not request.user.is_authenticated else request.user.profile.absolute_url),
        'name': (None if not request.user.is_authenticated else request.user.profile.name),
        'notificationsCount': 0,
    }
    if request.user.is_authenticated:
        if request.user.profile.avatar:
            current_user['avatar'] = sorl.thumbnail.get_thumbnail(
                request.user.profile.avatar, '128x128', crop='center', quality=80
            ).url
        current_user['notificationsCount'] = FeedEntry.objects.filter(
            user=request.user, is_read=False, category='notification',
        ).count()

    return {'current_user_js': current_user}
