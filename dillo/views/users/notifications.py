import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView
from django.shortcuts import reverse
from django.utils.text import slugify

from dillo.models.feeds import FeedEntry
from dillo.models.mixins import ApiResponseData
from dillo.templatetags.dillo_filters import compact_naturaltime

log = logging.getLogger(__name__)


class FeedNotificationsView(LoginRequiredMixin, ListView):
    template_name = 'dillo/notifications.pug'
    model = FeedEntry
    context_object_name = 'notifications'
    paginate_by = 5

    def get_queryset(self):
        return FeedEntry.objects.filter(user=self.request.user, category='notification',)


class ApiFeedNotificationsView(View):
    def get(self, request):
        r = ApiResponseData()

        notifications = FeedEntry.objects.filter(user=self.request.user, category='notification')
        r.count = notifications.count()
        paginator = Paginator(notifications, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        r.next_page_number = None if not page_obj.has_next() else page_obj.next_page_number()
        # If one more page is available, build a url to query it
        r.url_next_page = (
            None
            if not page_obj.has_next()
            else f"{reverse('api-notifications')}?page={page_obj.next_page_number()}"
        )
        for notification in page_obj.object_list:
            n = {
                'actor': {
                    'username': notification.action.actor.username,
                    'profileUrl': reverse(
                        'profile-detail', kwargs={'username': notification.action.actor.username}
                    ),
                },
                'verb': notification.action.verb,
                'verbSlug': slugify(notification.action.verb),
                'actionObjectUrl': notification.action.action_object.get_absolute_url(),
                'actionObject': str(notification.action.action_object),
                'timeSince': compact_naturaltime(notification.action.timestamp),
            }
            r.results.append(n)
        return JsonResponse(r.serialize())


class NotificationsMarkAsReadView(LoginRequiredMixin, View):
    def post(self, request):
        """Set unread notifications as read."""
        FeedEntry.objects.filter(user=request.user, category='notification', is_read=False,).update(
            is_read=True
        )
        log.debug('Marked unread notifications for user %s as read' % request.user)
        return JsonResponse({'status': 'success'})
