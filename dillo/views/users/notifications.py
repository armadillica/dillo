import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView

from dillo.models.feeds import FeedEntry

log = logging.getLogger(__name__)


class FeedNotificationsView(LoginRequiredMixin, ListView):
    template_name = 'dillo/notifications.pug'
    model = FeedEntry
    context_object_name = 'notifications'
    paginate_by = 5

    def get_queryset(self):
        return FeedEntry.objects.filter(user=self.request.user, category='notification',)


class NotificationsMarkAsReadView(LoginRequiredMixin, View):
    def post(self, request):
        """Set unread notifications as read."""
        FeedEntry.objects.filter(user=request.user, category='notification', is_read=False,).update(
            is_read=True
        )
        log.debug('Marked unread notifications for user %s as read' % request.user)
        return JsonResponse({'status': 'success'})
