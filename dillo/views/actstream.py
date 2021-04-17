import logging

from actstream import actions
from actstream.models import Follow
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View

log = logging.getLogger(__name__)


class FollowToggleView(LoginRequiredMixin, View):
    """Endpoint to toggle follow/unfollow for any object.

    This is typically called from a Vue component, which toggles the
    following status without reloading the entire page.
    """

    def get(self, request, *args, **kwargs):
        ctype = get_object_or_404(ContentType, pk=self.kwargs['content_type_id'])
        instance = get_object_or_404(ctype.model_class(), pk=self.kwargs['object_id'])
        is_followed = Follow.objects.is_following(self.request.user, instance)
        if is_followed:
            actions.unfollow(self.request.user, instance)
            action = "Unfollowed"
        else:
            actions.follow(self.request.user, instance)
            action = "Started Following"
        log.debug("%s %s %i" % (action, ctype.name, instance.id))
        return JsonResponse({'status': 'ok', 'action': action})
