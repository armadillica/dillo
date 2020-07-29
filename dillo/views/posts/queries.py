from actstream.models import followers
from django.urls import reverse
from django.shortcuts import get_object_or_404
from taggit.models import Tag

from dillo.models.posts import Post
from dillo.views.mixins import PostListView, PostListEmbedView


class PostByTagsListView(PostListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag_name = self.kwargs['tag_name']
        context['tag_name'] = tag_name
        # TODO(fsiddi) Refactor tag_name as tag.name
        context['tag'] = get_object_or_404(Tag, name=tag_name)
        context['tag_followers_count'] = len(followers(context['tag']))
        context['query_url'] = reverse('embed_posts_list_tag', kwargs={'tag_name': tag_name})
        return context


class PostSearchListView(PostListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_term = self.request.GET.get('q')
        context['query_url'] = "%s?q=%s" % (reverse('embed_posts_search'), search_term)
        return context


class PostsSearchEmbedView(PostListEmbedView):
    """Searched posts."""

    def get_queryset(self):
        """Fetch only published and public posts."""
        search_term = self.request.GET.get('q')
        queryset = Post.objects.filter(
            title__search=search_term, visibility='public', status='published',
        ).order_by('-published_at')
        return queryset


class PostsByTagListEmbedView(PostListEmbedView):
    """All posts with a certain tag."""

    def get_queryset(self):
        """Filter posts by tag, return 404 if no post is found."""
        queryset = Post.objects.filter(
            tags__name__in=[self.kwargs['tag_name']], status='published', visibility='public',
        ).order_by('-published_at')
        return queryset
