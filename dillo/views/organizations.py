import logging

from dataclasses import dataclass
from typing import Optional, List

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView

from dillo.models.cities import City
from dillo.models.organizations import Organization, OrganizationCategory
from dillo.tasks.emails import send_mail_superusers
from dillo.views.globe import get_globe_locations

log = logging.getLogger(__name__)


class OrganizationCreateView(LoginRequiredMixin, CreateView):

    template_name = 'dillo/organizations/organization_form.pug'

    model = Organization
    fields = [
        'name',
        'description',
        'country',
        'city',
        'website',
        'logo',
        'is_online',
        'categories',
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # form.fields['logo'].widget = ImageWidget()
        form.fields['city'].widget = forms.Select()
        form.fields['description'].widget = forms.Textarea(attrs={'rows': 3})
        form.fields['categories'].required = False
        return form

    def form_valid(self, form):
        # Set user as owner of the organization
        form.instance.user = self.request.user
        self.object: Organization = form.save()
        # Generate email notification
        organization_edit_url = reverse('admin:dillo_organization_change', args=[self.object.id])
        organization_edit_url_absolute = (
            f'http://{Site.objects.get_current().domain}{organization_edit_url}'
        )
        mail_body = f'New organization submission at {organization_edit_url_absolute}'
        send_mail_superusers('New Org Submission', mail_body)
        return HttpResponseRedirect(self.get_success_url())


class OrganizationUpdateView(LoginRequiredMixin, UpdateView):

    template_name = 'dillo/organizations/organization_form_update.pug'

    model = Organization
    fields = [
        'name',
        'description',
        'country',
        'city',
        'website',
        'logo',
        'is_online',
        'categories',
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # form.fields['logo'].widget = ImageWidget()
        form.fields['city'].widget = forms.Select()
        form.fields['description'].widget = forms.Textarea(attrs={'rows': 3})
        form.fields['categories'].required = False
        return form

    def dispatch(self, request, *args, **kwargs):
        """Ensure that only owners can update the organization."""
        obj = self.get_object()
        if obj.user != self.request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@dataclass
class SelectItem:
    value: int
    label: str
    is_selected: bool = False


@dataclass
class UrlParams:
    page: int
    categories: Optional[List]
    cities: Optional[List]

    def values_to_ints(self, prop_name):
        int_ids = []
        for f in getattr(self, prop_name):
            try:
                f = int(f)
            except ValueError:
                continue
            int_ids.append(f)
        setattr(self, prop_name, int_ids)

    def __post_init__(self):
        self.values_to_ints('categories')
        self.values_to_ints('cities')


@dataclass
class SearchFacets:
    categories: Optional[List[SelectItem]]
    cities: Optional[str]


class FilterMixin(TemplateView):
    url_params: UrlParams = None

    def dispatch(self, request, *args, **kwargs):
        def get_qs_list(param_name) -> List:
            qs = self.request.GET.getlist(param_name, default=[])
            if len(qs) == 1 and '' in qs:
                qs = []
            return qs

        def get_page() -> int:
            try:
                page = int(self.request.GET.get('page', 1))
            except ValueError:
                page = 1
            return page

        self.url_params = UrlParams(
            categories=get_qs_list('category'),
            cities=get_qs_list('city'),
            page=get_page(),
        )

        return super().dispatch(request, *args, **kwargs)

    def _facet_categories(self):
        categories_list = []
        for category in OrganizationCategory.objects.all():
            s = SelectItem(value=category.id, label=category.name)
            if category.name in self.url_params.categories:
                s.is_selected = True
            categories_list.append(s)
        return categories_list

    def _facet_cities(self):
        return City.objects.filter(id__in=self.url_params.cities)

    def search_facets(self):
        return SearchFacets(
            categories=self._facet_categories(),
            cities=self._facet_cities(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_params'] = self.url_params
        context['search_facets'] = self.search_facets()
        return context


class OrganizationListView(FilterMixin):
    template_name = 'dillo/organizations/organization_directory.pug'


class ApiOrganizationListView(FilterMixin):
    template_name = 'dillo/organizations/organization_list_embed.pug'

    def get_queryset(self):
        qs = Organization.objects.filter(visibility=Organization.Visibilities.PUBLIC).order_by('pk')
        if self.url_params.categories:
            qs = qs.filter(categories__in=self.url_params.categories).distinct()
        if self.url_params.cities:
            qs = qs.filter(city_ref_id__in=self.url_params.cities).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(self.get_queryset(), 25)
        context['page_obj'] = paginator.get_page(self.url_params.page)
        return context


class ApiOrganizationGlobeView(FilterMixin):
    def get(self, request, *args, **kwargs):
        qs = (
            Organization.objects.filter(visibility=Organization.Visibilities.PUBLIC)
            .filter(city_ref__isnull=False)
            .prefetch_related('city_ref')
            .values('city_ref_id', 'city_ref__lat', 'city_ref__lng', 'city_ref__name')
            .annotate(count=Count('city_ref_id'))
        )
        if self.url_params.categories:
            qs = qs.filter(categories__in=self.url_params.categories).distinct()

        locations = get_globe_locations(qs)

        return JsonResponse({'locations': locations})
