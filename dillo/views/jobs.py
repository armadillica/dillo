import logging
import re

from dataclasses import dataclass
from typing import Optional, List

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


@dataclass
class UrlParams:
    contract_type: Optional[str]
    is_remote_friendly: Optional[str]
    software: Optional[str]
    level: Optional[str]

    @property
    def software_label(self):
        return self.software or 'Software'

    @property
    def level_label(self):
        return self.level or 'Level'

    @property
    def contract_type_label(self):
        return self.contract_type or 'Contract Type'


@dataclass
class SearchFacets:
    contract_type: Optional[List[str]]
    software: Optional[List[str]]
    level: Optional[List[str]]

    # @property
    # def tag_qs(self):
    #     return '' if not self.tag else f'&tag={self.tag}'
    #
    # @property
    # def sort_qs(self):
    #     return f'sort={self.sort}'
    #
    # @property
    # def submitted_by_qs(self):
    #     return '' if not self.submitted_by else f'&submitted-by={self.submitted_by}'
    #


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

    url_params: UrlParams = None

    @staticmethod
    def _facet_software():
        software_set = set()
        software = Job.objects.all().distinct('software').values_list('software')
        for s in software:
            for n in re.split(',|/', s[0]):
                n = n.strip()
                software_set.add(n)

        return sorted(software_set)

    @staticmethod
    def _facet_level():
        level_set = set()
        levels = Job.objects.all().distinct('level').values_list('level')
        for level in levels:
            for lev in re.split(',|/', level[0]):
                lev = lev.strip()
                level_set.add(lev)
        return sorted(level_set)

    @staticmethod
    def _facet_contract_type():
        return [ct[0] for ct in Job.CONTRACT_TYPES]

    def search_facets(self):
        return SearchFacets(
            contract_type=self._facet_contract_type(),
            software=self._facet_software(),
            level=self._facet_level(),
        )

    def dispatch(self, request, *args, **kwargs):
        self.url_params = UrlParams(
            contract_type=self.request.GET.get('contract-type'),
            is_remote_friendly=self.request.GET.get('is-remote-friendly'),
            software=self.request.GET.get('software'),
            level=self.request.GET.get('level'),
        )

        return super(JobListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Job.objects.filter(visibility='public').order_by('-created_at', 'title')
        if self.url_params.software:
            qs = qs.filter(software__icontains=self.url_params.software)
        if self.url_params.is_remote_friendly:
            qs = qs.filter(is_remote_friendly=True)
        if self.url_params.level:
            qs = qs.filter(level__icontains=self.url_params.level)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Animation Jobs on anima.to",
            description="Public jobs board for the world of animation",
            image_field=None,
            image_alt=None,
        )
        context['url_params'] = self.url_params
        context['search_facets'] = self.search_facets()
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
