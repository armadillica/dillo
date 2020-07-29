from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from dillo.models.posts import Post
from dillo.views.mixins import PostListView, PostListEmbedView


class BookmarksView(LoginRequiredMixin, PostListView):
    """Display user bookmarks."""

    template_name = 'dillo/posts_base.pug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_url'] = reverse('embed_bookmarks')
        return context


class BookmarksEmbedView(LoginRequiredMixin, PostListEmbedView):
    """Bookmarked posts."""

    def get_queryset(self):
        """Fetch only bookmarked posts."""
        return self.request.user.profile.bookmarks.all()


class BookmarkPostView(LoginRequiredMixin, View):
    """Add or remove the post from the User's bookmarks."""

    # TODO(fsiddi) convert to function-based view
    def post(self, request, *args, **kwargs):
        # Check if user already bookmarked post
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if request.user.profile.bookmarks.filter(pk=post.id).exists():
            request.user.profile.bookmarks.remove(post)
            action = 'removed'
        else:
            request.user.profile.bookmarks.add(post)
            action = 'added'
        return JsonResponse({'action': action, 'status': 'success'})
