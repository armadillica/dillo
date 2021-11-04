from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View

from dillo.views.mixins import PostListEmbedView


class HomepageRouter(View):
    def get(self, request, *args, **kwargs):
        explore_url = reverse('explore') + '?layout=grid'
        return HttpResponseRedirect(explore_url)
        # explore_feed_url = reverse('explore-feed') + '?layout=list'
        # return HttpResponseRedirect(explore_feed_url)


class PostsStreamUserListEmbedView(LoginRequiredMixin, PostListEmbedView):
    """The User stream."""

    def get_queryset(self):
        return (
            self.request.user.feed_entries.filter(category='timeline')
            .select_related('action')
            .order_by('action___timestamp')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        """Replace activity list with posts list."""
        context['posts'] = [p.action.action_object for p in context['posts']]
        return context
