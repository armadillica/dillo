import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, ListView, DetailView

from dillo.models.shorts import Short
from dillo.views.mixins import OgData

log = logging.getLogger(__name__)


class ShortCreateView(LoginRequiredMixin, CreateView):

    template_name = 'dillo/shorts/short_form.pug'

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

    template_name = 'dillo/shorts/short_form_update.pug'

    model = Short
    fields = ['title', 'description', 'image']

    def dispatch(self, request, *args, **kwargs):
        """Ensure that only owners can update the short."""
        obj = self.get_object()
        if obj.user != self.request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ShortListView(ListView):

    paginate_by = 12
    template_name = 'dillo/shorts/short_list.pug'

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

    template_name = 'dillo/shorts/short_detail.pug'
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
