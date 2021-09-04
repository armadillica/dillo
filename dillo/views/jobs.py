import logging

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from dillo.views.mixins import OgData
from dillo.models.jobs import Job
from dillo.tasks.emails import send_mail_superusers

log = logging.getLogger(__name__)


class JobCreateView(LoginRequiredMixin, CreateView):

    template_name = 'dillo/jobs/job_form.pug'

    model = Job
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
        form.fields['title'].widget = forms.TextInput()
        return form

    def form_valid(self, form):
        # Set user as owner of the job
        form.instance.user = self.request.user
        form.instance.visibility = 'unlisted'
        self.object: Job = form.save()
        # Generate email notification
        job_edit_url = reverse('admin:dillo_job_change', args=[self.object.id])
        job_edit_url_absolute = f'http://{Site.objects.get_current().domain}{job_edit_url}'
        mail_body = f'New job submission at {job_edit_url_absolute}'
        send_mail_superusers('New Job Submission', mail_body)
        return HttpResponseRedirect(self.get_success_url())


class JobUpdateView(LoginRequiredMixin, UpdateView):

    template_name = 'dillo/jobs/job_form_update.pug'

    model = Job
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
        form.fields['title'].widget = forms.TextInput()
        return form

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
        jobs = Job.objects.filter(visibility='public').order_by('-created_at', 'title')
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
    model = Job

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
