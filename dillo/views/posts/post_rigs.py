import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from dillo.views.mixins import OgData
from dillo.models.post_rigs import Rig

log = logging.getLogger(__name__)


class RigCreateView(LoginRequiredMixin, CreateView):

    model = Rig
    template_name = 'dillo/rigs/rig_form.pug'
    fields = ['name', 'url', 'description', 'image', 'software']

    def form_valid(self, form):
        # Set user as owner of the rig
        form.instance.user = self.request.user
        return super().form_valid(form)


class RigUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):

    template_name = 'dillo/rigs/rig_form_update.pug'

    model = Rig
    fields = ['name', 'description', 'image', 'software']

    def test_func(self):
        """Ensure that only owners can update the rig."""
        obj = self.get_object()
        return obj.user == self.request.user


class RigListView(ListView):

    paginate_by = 32
    template_name = 'dillo/rigs/rig_list.pug'

    def get_queryset(self):
        submitted_by = self.request.GET.get('submitted-by') or None
        rigs = Rig.objects.filter(visibility='public')
        if submitted_by:
            try:
                submitted_by = int(submitted_by)
                rigs = rigs.filter(user_id__exact=submitted_by)
            except ValueError:
                log.warning('Trying to folder rigs by %s' % submitted_by)
        # List the latest rigs first
        return rigs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Rigs on anima.to",
            description="Curated collection of rigs.",
            image_field=None,
            image_alt=None,
        )
        return context


class RigDetailView(DetailView):

    template_name = 'dillo/rigs/rig_detail.pug'
    model = Rig

    def populate_og_data(self):
        """Prepare the OgData object for the context."""
        rig: Rig = self.object

        image_field = None
        # Try to use the rig image (it's a poster image, so it will be cropped)
        if rig.image:
            image_field = rig.image

        image_alt = f"{rig.name} on anima.to"

        return OgData(
            title=rig.name,
            description=rig.description,
            image_field=image_field,
            image_alt=image_alt,
        )

    def get_adjacent_rigs(self, rig_id):
        """Given a Rig id, find the previous and the next one."""
        try:
            # Get the next rig
            next_rig = Rig.objects.filter(visibility='public', id__gt=rig_id).order_by(
                'created_at'
            )[0]
        except IndexError:
            log.debug("No prev_rig found, end of the list")
            next_rig = None

        try:
            # Get the previous rig
            prev_rig = Rig.objects.filter(visibility='public', id__lt=rig_id).order_by(
                '-created_at'
            )[0]
        except IndexError:
            log.debug("No prev_rig found, end of the list")
            prev_rig = None

        prev_rig_url = (
            None if prev_rig is None else reverse('rig-detail', kwargs={'pk': prev_rig.id})
        )

        next_rig_url = (
            None if next_rig is None else reverse('rig-detail', kwargs={'pk': next_rig.id})
        )

        return prev_rig_url, next_rig_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_rig_id = context['object'].id
        context['rig'] = context['object']
        context['prev_rig_url'], context['next_rig_url'] = self.get_adjacent_rigs(current_rig_id)
        context['og_data'] = self.populate_og_data()
        return context
