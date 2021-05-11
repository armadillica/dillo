import re
import urllib.parse
from django import template
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import mark_safe, escape
from django.template.defaultfilters import stringfilter
from django.contrib.humanize.templatetags.humanize import naturaltime

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


@register.filter
def markdown_with_shortcodes(value):
    return shortcode_render(markdown_render(value))
