import re
import requests
import urllib.parse
from django import template
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import mark_safe, escape
from django.template.defaultfilters import stringfilter
from django.contrib.humanize.templatetags.humanize import naturaltime

from bleach import linkifier
from bleach.linkifier import build_url_re
from bs4 import BeautifulSoup

from dillo.shortcodes import render as shortcode_render
from dillo.markdown import render as markdown_render
import dillo.models.posts

find_hashtags_re = re.compile(r'\B#\w*[a-zA-Z]+\w*')
find_mentions_re = re.compile(r'\B@\w*[a-zA-Z]+\w*')

register = template.Library()


def tag_match_to_url(tag):
    """Convert a regex match to a tag url."""
    # TODO(fsiddi) when moving to Python 3.7, specify the type of tag (re.Match)
    tag_name = tag.group(0)
    tag_url = reverse('posts_list_tag', kwargs={'tag_name': tag_name[1:]})
    return f'<a href="{tag_url}">{tag_name}</a>'


def mention_match_to_url(mention):
    mention = mention.group(0)
    if not User.objects.filter(username=mention[1:]).exists():
        return mention
    mention_url = reverse('profile-detail', kwargs={'username': mention[1:]})
    return f'<a href="{mention_url}">{mention}</a>'


@register.filter
@stringfilter
def linkify_tags_and_mentions(value):
    """Parses a text and replaces tags with links."""
    value = find_hashtags_re.sub(tag_match_to_url, escape(value))
    value = find_mentions_re.sub(mention_match_to_url, value)
    # value = link_tags_parse(value)
    return mark_safe(value)


@register.filter
def shorten_timesince(timesince):
    """Shorten the timesince filter by taking only the first part."""

    timesince = timesince.split(',', 1)[0]
    return timesince


@register.filter
def compact_timesince(timesince):
    """Make timesince filter super compact."""

    # Replace long words with letters. (2 days, 3 hours -> 2 d, 3 h)
    timesince = timesince.replace('seconds', 's').replace('second', 's')
    timesince = timesince.replace('minutes', 'm').replace('minute', 'm')
    timesince = timesince.replace('hours', 'h').replace('hour', 'h')
    timesince = timesince.replace('days', 'd').replace('day', 'd')
    timesince = timesince.replace('months', 'mo').replace('month', 'mo')
    timesince = timesince.replace('weeks', 'w').replace('week', 'w')
    timesince = timesince.replace('years', 'w').replace('year', 'y')

    # Remove 'an, ago'.
    timesince = timesince.replace('ago', '').replace('an', '')

    # Remove space between digit and unit. (2 d, 3h -> 2d, 3h)
    timesince = timesince.replace('\xa0', '')

    # Take only the first, usually interesting part. (2d, 3h -> 2d)
    timesince = timesince.split(',', 1)[0]
    return timesince


@register.filter
def compact_naturaltime(time):
    """Make naturaltime super compact."""

    if not time:
        return

    # e.g. 15 days, 3 hours -> 15d, 3h
    time = naturaltime(time)
    time = compact_timesince(time)
    return time


@register.filter
def compact_number(value: int) -> str:
    """Format number in a compact way when the value is above 1000."""
    value = float('{:.3g}'.format(value))
    magnitude = 0
    while abs(value) >= 1000:
        magnitude += 1
        value /= 1000.0
    return '{}{}'.format(
        '{:f}'.format(value).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude]
    )


@register.filter
def website_hostname(url):
    """Given a website url, return the hostname only.

    This useful for showing a url in the frontend. For example:
    https://blender.org -> blender.org
    """

    url = urllib.parse.urlparse(url)
    hostname = url.hostname.replace("www.", "")
    return hostname


@register.filter
def is_liked(value, user: User):
    """Check if an item was liked by the current user."""
    return value.is_liked(user)


@register.filter
def is_attended(value, user: User):
    """Check if an item (Event) is attended by the current user."""
    return value.is_attended(user)


@register.filter
def is_bookmarked(value, user: User):
    """Check if a Post was bookmarked by the current user."""
    if not isinstance(value, dillo.models.posts.Post):
        raise TypeError('Value should be Post')
    return value.is_bookmarked(user)


def add_class_to_tag(markup, tag_type, classes):
    """Find specific tags in the markup and add classes to them."""
    soup = BeautifulSoup(markup, "html.parser")
    elements = soup.find_all(tag_type)

    for el in elements:
        el['class'] = el.get('class', []) + [classes]

    return soup.prettify(soup.original_encoding)


def parse_phabricator_tasks(markup):
    """Look for phabricator tasks/diffs and retrieve their name and status."""
    soup = BeautifulSoup(markup, "html.parser")
    dbo = soup.find_all('a', {'href': re.compile(r'\/developer.blender.org\/[T+D]+([0-9]{1,6})*')})

    for url in dbo:
        parse_url = urllib.parse.urlparse(url.get('href'))
        path = parse_url.path
        ob_id = str(path[2:])

        # Parse tasks.
        if path.startswith('/T'):
            query_url = 'https://developer.blender.org/api/maniphest.info'
            data = {
            'api.token': settings.PHABRICATOR_API_TOKEN,
            'task_id': ob_id
            }

            try:
                response = requests.post(query_url, data=data)
                r = response.json()
                r = r['result']

                if r:
                    title = '{0}: {1} [{2}]'.format(r['objectName'], r['title'], r['statusName'])
                    url.string = title
                    status = 'is-status-closed' if r['isClosed'] else 'is-status-{0}'.format(r['status'])
                    url['class'] = url.get('class', []) + ['is-blender-developer is-external-special', status]
            except requests.exceptions.RequestException:
                continue

        # Parse diffs.
        if path.startswith('/D'):
            query_url = 'https://developer.blender.org/api/differential.query'
            data = {
            'api.token': settings.PHABRICATOR_API_TOKEN,
            'ids[0]': ob_id
            }

            try:
                response = requests.post(query_url, data=data)
                r = response.json()
                r = r['result']

                if r and r[0]:
                    r = r[0]
                    title = 'D{0}: {1} [{2}]'.format(r['id'], r['title'], r['statusName'])
                    url.string = title
                    status = 'is-status-{0}'.format(r['status'])
                    url['class'] = url.get('class', []) + ['is-blender-developer is-external-special', status]
            except requests.exceptions.RequestException:
                continue

    return soup.prettify(soup.original_encoding)


def parse_links(markup):
    """Parse to add target, nofollow, and include missing TLDs"""

    # Add missing top-level domains to linkfify.
    # Workaround from https://github.com/mozilla/bleach/issues/519
    tlds = linkifier.TLDS
    tlds.append(u'chat')
    tlds.append(u'cloud')
    tlds.append(u'community')
    tlds.append(u'fund')
    tlds.append(u'today')

    improved_url_re = build_url_re(tlds=tlds)

    def set_target(attrs, new=False):
        p = urllib.parse.urlparse(attrs[(None, 'href')])
        # TODO: get URL from request to figure out if it's an internal link.
        if p.netloc not in ['blender.community']:
            attrs[(None, 'target')] = '_blank'
            attrs[(None, 'rel')] = 'nofollow'
            attrs[(None, 'class')] = 'is-external'
        return attrs

    skip_tags = ['code', 'pre']
    linker = linkifier.Linker(url_re=improved_url_re, callbacks=[set_target], skip_tags=skip_tags)
    markup = linker.linkify(markup)
    markup = parse_phabricator_tasks(markup)

    return markup


@register.filter
def make_images_expandable(markup):
    """Mark <img> tags as expandable"""
    classes = 'media-embed-image expand js-media-expand'
    return add_class_to_tag(markup, 'img', classes)


@register.filter
def markdown_with_shortcodes(value):
    return shortcode_render(markdown_render(value))


@register.filter
def markdown_with_parsed_tags_and_shortcodes(value):
    """Same as markdown_with_shortcodes with special parsing"""
    markup = shortcode_render(markdown_render(value))
    markup = parse_links(markup)
    markup = make_images_expandable(markup)

    return markup
