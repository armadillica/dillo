from django.conf import settings
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
