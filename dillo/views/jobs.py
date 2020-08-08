import logging

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from dillo.views.mixins import OgData
from dillo.models.posts import PostJob

log = logging.getLogger(__name__)


class JobCreateView(LoginRequiredMixin, CreateView):

    template_name = 'dillo/jobs/job_form.pug'

    model = PostJob
    fields = [
        'title',
        'company',
        'city',
        'province_state',
        'country',
        'contract_type',
        'is_remote_friendly',
        'description',
        'image',
        'url_apply',
        'studio_website',
        'starts_at',
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['starts_at'].widget = forms.TextInput(attrs={'type': 'date'})
        return form

    def form_valid(self, form):
        # Set user as owner of the short
        form.instance.user = self.request.user
        form.instance.visibility = 'unlisted'
        return super().form_valid(form)


class JobUpdateView(LoginRequiredMixin, UpdateView):

    template_name = 'dillo/jobs/job_form_update.pug'

    model = PostJob
    fields = [
        'title',
        'company',
        'city',
        'province_state',
        'country',
        'contract_type',
        'is_remote_friendly',
        'description',
        'image',
        'url_apply',
        'studio_website',
        'starts_at',
    ]

    def dispatch(self, request, *args, **kwargs):
        """Ensure that only owners can update the short."""
        obj = self.get_object()
        if obj.user != self.request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class JobListView(ListView):

    paginate_by = 50
    template_name = 'dillo/jobs/job_list.pug'
    context_object_name = 'jobs'

    def get_queryset(self):
        jobs = PostJob.objects.filter(visibility='public').order_by('-created_at', 'title')
        return jobs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Animation Jobs on anima.to",
            description="Public jobs board for the world of animation",
            image_field=None,
            image_alt=None,
        )
        return context


class JobDetailView(DetailView):

    template_name = 'dillo/jobs/job_detail.pug'
    model = PostJob

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title = f"{self.object.title} at {self.object.company}"
        context['og_data'] = OgData(
            title=title,
            description=self.object.description,
            image_field=None,
            image_alt=f"{title} on anima.to",
        )
        return context
