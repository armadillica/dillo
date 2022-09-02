import logging
from dataclasses import dataclass
from typing import Optional, List

from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView


from dillo.models.profiles import City, Profile, Badge

log = logging.getLogger(__name__)


@dataclass
class SelectItem:
    value: int
    label: str
    is_selected: bool = False


@dataclass
class UrlParams:
    sort: str
    badges: Optional[List]
    tags: Optional[List]
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
        self.values_to_ints('badges')
        self.values_to_ints('cities')
        if self.sort not in {'-likes_count', '-posts_count', '-views_count'}:
            self.sort = '-likes_count'


@dataclass
class SearchFacets:
    badges: Optional[List[SelectItem]]
    tags: Optional[List[SelectItem]]
    cities: Optional[str]


def globe_view(request):
    locations = []
    users = (
        Profile.objects.filter(city_ref__isnull=False)
        .prefetch_related('city_ref')
        .values('city_ref_id', 'city_ref__lat', 'city_ref__lng', 'city_ref__name')
        .annotate(count=Count('city_ref_id'))
    )
    for u in users:
        locations.append(
            {
                'lat': u['city_ref__lat'],
                'lng': u['city_ref__lng'],
                'label': '',
                'cityId': u['city_ref_id'],
                'cityName': u['city_ref__name'],
                'count': u['count'],
            }
        )
    return render(request, 'dillo/directory/user_globe.pug', {'locations': locations})


def api_city_in_country(request, country_code):
    cities = City.objects.filter(country=country_code.upper())
    return JsonResponse({'cities': [{'value': city.name, 'label': city.name} for city in cities]})


class FilterMixin(TemplateView):
    url_params: UrlParams = None

    def dispatch(self, request, *args, **kwargs):
        def get_qs_list(param_name) -> List:
            qs = self.request.GET.getlist(param_name, default=[])
            if len(qs) == 1 and '' in qs:
                qs = []
            return qs

        self.url_params = UrlParams(
            tags=get_qs_list('tag'),
            badges=get_qs_list('badge'),
            cities=get_qs_list('city'),
            sort=self.request.GET.get('sort', '-likes_count'),
        )

        return super().dispatch(request, *args, **kwargs)

    def _facet_badges(self):
        badges = []
        for badge in Badge.objects.all():
            s = SelectItem(value=badge.id, label=badge.name)
            if badge.id in self.url_params.badges:
                s.is_selected = True
            badges.append(s)
        return badges

    def _facet_tags(self):
        tags_list = []
        for tag in Profile.tags.all():
            s = SelectItem(value=tag.name, label=tag.name)
            if tag.name in self.url_params.tags:
                s.is_selected = True
            tags_list.append(s)
        return tags_list

    def _facet_cities(self):
        return City.objects.filter(id__in=self.url_params.cities)

    def search_facets(self):
        return SearchFacets(
            badges=self._facet_badges(),
            tags=self._facet_tags(),
            cities=self._facet_cities(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_params'] = self.url_params
        context['search_facets'] = self.search_facets()
        context['sort'] = self.url_params.sort
        return context


class UserListView(FilterMixin):
    template_name = 'dillo/directory/user_directory.pug'


class ApiUserListView(FilterMixin):
    template_name = 'dillo/directory/user_list_embed.pug'

    def get_queryset(self):
        qs = (
            Profile.objects.filter(user__is_active=True)
            .prefetch_related('badges')
            .prefetch_related('user__post_set')
            .annotate(posts_count=Count('user__post'))
            .order_by(self.url_params.sort)
        )
        if self.url_params.tags:
            qs = qs.filter(tags__name__in=self.url_params.tags).distinct()
        if self.url_params.badges:
            qs = qs.filter(badges__in=self.url_params.badges).distinct()
        if self.url_params.cities:
            qs = qs.filter(city_ref_id__in=self.url_params.cities).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(self.get_queryset(), 25)
        page_obj = paginator.get_page(1)
        context['object_list'] = page_obj
        return context


class ApiUserGlobeView(FilterMixin):
    def get(self, request, *args, **kwargs):
        locations = []
        qs = (
            Profile.objects.filter(user__is_active=True)
            .filter(city_ref__isnull=False)
            .order_by('-likes_count')
            .prefetch_related('city_ref')
            .values('city_ref_id', 'city_ref__lat', 'city_ref__lng', 'city_ref__name')
            .annotate(count=Count('city_ref_id'))
        )
        if self.url_params.tags:
            qs = qs.filter(tags__name__in=self.url_params.tags).distinct()
        if self.url_params.badges:
            qs = qs.filter(badges__in=self.url_params.badges).distinct()

        for profile in qs:
            locations.append(
                {
                    'lat': profile['city_ref__lat'],
                    'lng': profile['city_ref__lng'],
                    'label': '',
                    'cityId': profile['city_ref_id'],
                    'cityName': profile['city_ref__name'],
                    'count': profile['count'],
                }
            )
        return JsonResponse({'locations': locations})
