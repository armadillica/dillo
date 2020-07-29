from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse

from dillo.models.posts import Post
from dillo.views.mixins import PostListView, PostListEmbedView


class HomepageView(PostListView):
    """Homepage. Display the user feed."""

    template_name = 'dillo/posts_base.pug'

    def get(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            return HttpResponseRedirect(reverse('explore'))
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_url'] = reverse('embed_stream')
        processing_posts = Post.objects.filter(
            status='processing', user=self.request.user, visibility='public'
        )
        context['processing_posts'] = {'posts': [str(post.hash_id) for post in processing_posts]}
        return context


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
