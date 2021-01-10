import logging

from django.views.generic.detail import DetailView

from dillo.views.mixins import OgData
from dillo.models.communities import Community

log = logging.getLogger(__name__)


class CommunityDetailView(DetailView):

    template_name = 'dillo/communities/community_detail.pug'
    model = Community

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title=self.object.name,
            description=self.object.tagline,
            image_field=None,
            image_alt=self.object.name,
        )
        return context
