import logging

from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from dillo.models.profiles import Profile
from dillo.views.mixins import OgData

log = logging.getLogger(__name__)


class ReelListView(ListView):

    # Multiple of 4, so the 4-items-per-row grid is complete.
    paginate_by = 48
    template_name = 'dillo/reels/reel_list.pug'

    def get_queryset(self):
        """Get Profiles, sorted by creation date or most likes."""
        sort = self.request.GET.get('sort') or None
        qs = Profile.objects.exclude(reel__exact='')
        if sort == 'recent':
            qs = qs.order_by('-created_at', 'user_id')
        else:
            qs = qs.order_by('-likes_count', 'user_id')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Animation Reels on anima.to",
            description="Collection of reels from the world of animation.",
            image_field=None,
            image_alt=None,
        )
        sort = self.request.GET.get('sort')
        # Build 'sort' query argument to use in the _pagination.pug component
        # This allows to perform correct pagination
        if sort == 'recent':
            context['sort'] = 'sort=recent'
        return context


class ReelDetailView(DetailView):

    template_name = 'dillo/reels/reel_detail.pug'
    model = User
    context_object_name = 'user'

    def get_adjacent_profiles_with_reels(self):
        """Given a User id, find the previous and the next reel."""
        profiles = Profile.objects.exclude(reel__exact='').order_by('-likes_count', 'user_id')
        profiles_list = list(profiles)
        # Faster idx, no needed yet
        # idx = list(next_profiles.values_list('user_id', flat=True)).index(self.object.user.id)
        idx = profiles_list.index(self.object.profile)
        try:
            next_profile = profiles_list[idx + 1]
        except IndexError:
            log.debug("No next_profile found, end of the list")
            next_profile = None

        if idx == 0:
            log.debug("No prev_profile found, end of the list")
            prev_profile = None
        else:
            prev_profile = profiles_list[idx - 1]

        prev_profile_url = (
            None
            if prev_profile is None
            else reverse('reel-detail', kwargs={'profile_id': prev_profile.user.id})
        )

        next_profile_url = (
            None
            if next_profile is None
            else reverse('reel-detail', kwargs={'profile_id': next_profile.user.id})
        )

        return prev_profile_url, next_profile_url

    def get_object(self, queryset=None):
        profile = get_object_or_404(Profile, pk=self.kwargs['profile_id'])
        if not profile.reel:
            raise Http404("This Profile has no reel")
        return profile.user

    def populate_og_data(self):
        """Prepare the OgData object for the context."""
        user = self.object
        title = user.username if not user.profile.name else user.profile.name

        image_field = None
        # Try to use the reel_thumbnail
        if user.profile.reel_thumbnail_16_9:
            image_field = user.profile.reel_thumbnail_16_9
        # Otherwise use the avatar
        elif user.profile.avatar:
            image_field = user.profile.avatar

        image_alt = f"{title} on anima.to"

        return OgData(
            title=title, description=user.profile.bio, image_field=image_field, image_alt=image_alt,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (
            context['prev_profile_url'],
            context['next_profile_url'],
        ) = self.get_adjacent_profiles_with_reels()
        context['query_url'] = reverse(
            'posts_by_user_list', kwargs={'user_id': context['object'].id}
        )
        context['layout'] = 'grid'
        context['og_data'] = self.populate_og_data()
        return context
