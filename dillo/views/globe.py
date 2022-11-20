from django.http import JsonResponse

from dillo.models.cities import City


def api_city_in_country(request, country_code):
    cities = City.objects.filter(country=country_code.upper())
    return JsonResponse({'cities': [{'value': city.name, 'label': city.name} for city in cities]})


def get_globe_locations(items):
    locations = []
    for i in items:
        locations.append(
            {
                'lat': i['city_ref__lat'],
                'lng': i['city_ref__lng'],
                'label': '',
                'cityId': i['city_ref_id'],
                'cityName': i['city_ref__name'],
                'count': i['count'],
            }
        )
    return locations
