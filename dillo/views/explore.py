from actstream.models import Action
from django.urls import reverse
from django.views.generic import ListView
from dillo.views.mixins import PostListView


class ExploreFeedView(PostListView):
    @staticmethod
    def get_query_url():
        return reverse('embed-explore-feed')


class ExploreFeedEmbedView(ListView):
    """List of all relevant activities."""

    model = Action

    def get_queryset(self):
        return Action.objects.filter(
            extra__is_on_explore_feed=True, extra__parent_action__isnull=True
        )

    def get_template_names(self):
        current_layout = self.request.session.get('layout', 'list')
        next_layout = self.request.GET.get('layout', current_layout)  # 'list' or 'grid'
        if current_layout != next_layout:
            self.request.session['layout'] = next_layout
        if next_layout == 'list':
            return ['dillo/feeds/explore_list_embed.pug']
        elif next_layout == 'grid':
            return ['dillo/feeds/explore_grid_embed.pug']

    def get_paginate_by(self, queryset):
        current_layout = self.request.session.get('layout', 'list')
        next_layout = self.request.GET.get('layout', current_layout)
        if next_layout == 'list':
            return 5
        elif next_layout == 'grid':
            return 15
