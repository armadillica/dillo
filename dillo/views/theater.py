import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from dillo.models.profiles import Profile
from dillo.models.shorts import Short
from dillo.views.mixins import OgData

log = logging.getLogger(__name__)


class ReelListView(ListView):

    # Multiple of 4, so the 4-items-per-row grid is complete.
    paginate_by = 48
    template_name = 'dillo/theater/reel_list.pug'

    def get_queryset(self):
        return Profile.objects.exclude(reel__exact='').order_by('-likes_count', 'user_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Animation Reels on anima.to",
            description="Collection of reels from the world of animation.",
            image_field=None,
            image_alt=None,
        )
        return context


class ReelDetailView(DetailView):

    template_name = 'dillo/theater/reel_detail.pug'
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


class ShortCreateView(LoginRequiredMixin, CreateView):

    template_name = 'dillo/theater/short_form.pug'

    model = Short
    fields = [
        'title',
        'url',
    ]

    def form_valid(self, form):
        # Set user as owner of the short
        form.instance.user = self.request.user
        return super().form_valid(form)


class ShortUpdateView(LoginRequiredMixin, UpdateView):

    template_name = 'dillo/theater/short_form_update.pug'

    model = Short
    fields = ['title', 'description', 'image']

    def dispatch(self, request, *args, **kwargs):
        """Ensure that only owners can update the short."""
        obj = self.get_object()
        if obj.user != self.request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ShortListView(ListView):

    paginate_by = 8
    template_name = 'dillo/theater/short_list.pug'

    def get_queryset(self):
        submitted_by = self.request.GET.get('submitted-by') or None
        shorts = Short.objects.filter(visibility='public')
        if submitted_by:
            try:
                submitted_by = int(submitted_by)
                shorts = shorts.filter(user_id__exact=submitted_by)
            except ValueError:
                log.warning('Trying to folder shorts by %s' % submitted_by)

        return shorts.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Animated Shorts on anima.to",
            description="Curated collection of animated shorts.",
            image_field=None,
            image_alt=None,
        )
        return context


class ShortDetailView(DetailView):

    template_name = 'dillo/theater/short_detail.pug'
    model = Short

    def populate_og_data(self):
        """Prepare the OgData object for the context."""
        short = self.object

        image_field = None
        if short.image:
            image_field = short.image

        image_alt = f"{short.title} on anima.to"

        return OgData(
            title=short.title, description='', image_field=image_field, image_alt=image_alt,
        )

    def get_adjacent_shorts(self, short_id):
        """Given a Short id, find the previous and the next one.

        TODO (fsiddi): Add tests for this
        """
        try:
            # Get the next short
            next_short = Short.objects.filter(visibility='public', id__gt=short_id).order_by(
                'created_at'
            )[0]
        except IndexError:
            log.debug("No prev_short found, end of the list")
            next_short = None

        try:
            # Get the previous short
            prev_short = Short.objects.filter(visibility='public', id__lt=short_id).order_by(
                '-created_at'
            )[0]
        except IndexError:
            log.debug("No prev_short found, end of the list")
            prev_short = None

        prev_short_url = (
            None if prev_short is None else reverse('short-detail', kwargs={'pk': prev_short.id})
        )

        next_short_url = (
            None if next_short is None else reverse('short-detail', kwargs={'pk': next_short.id})
        )

        return prev_short_url, next_short_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_short_id = context['object'].id
        context['prev_short_url'], context['next_short_url'] = self.get_adjacent_shorts(
            current_short_id
        )
        context['og_data'] = self.populate_og_data()
        return context
