import math
import bleach
import httplib
from urlparse import urlparse

from application import app
from application import redis_client

from flask.ext.security import current_user
from flask.ext.cache import make_template_fragment_key

ALPHABET = "bcdfghjklmnpqrstvwxyz0123456789BCDFGHJKLMNPQRSTVWXYZ"
BASE = len(ALPHABET)
MAXLEN = 6

def encode_id(n):
    pad = MAXLEN - 1
    n = int(n + pow(BASE, pad))

    s = []
    t = int(math.log(n, BASE))
    while True:
        bcp = int(pow(BASE, t))
        a = int(n / bcp) % BASE
        s.append(ALPHABET[a:a+1])
        n = n - (a * bcp)
        t -= 1
        if t < 0: break

    return "".join(reversed(s))

def decode_id(n):
    n = "".join(reversed(n))
    s = 0
    l = len(n) - 1
    t = 0
    while True:
        bcpow = int(pow(BASE, l - t))
        s = s + ALPHABET.index(n[t:t+1]) * bcpow
        t += 1
        if t > l: break

    pad = MAXLEN - 1
    s = int(s - pow(BASE, pad))

    return int(s)


import re
import translitcodec

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = word.encode('translit/long')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time 
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff <= 7:
        return str(day_diff) + " days ago"
    if day_diff <= 31:
        week_count = day_diff/7
        if week_count == 1:
            return str(week_count) + " week ago"
        else:
            return str(week_count) + " weeks ago"
    if day_diff <= 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"


def bleach_input(markup):
    ALLOWED_TAGS = [u'a', u'abbr', u'acronym', u'b', u'blockquote', u'code', u'em', u'i', u'li', u'ol', u'strong', u'ul', u'p']
    output = bleach.clean(markup, tags=ALLOWED_TAGS, strip=False)
    return output


def check_url(url):
    p = urlparse(url)
    conn = httplib.HTTPConnection(p.netloc)
    conn.request('HEAD', p.path)
    resp = conn.getresponse()
    return resp.status < 400


def make_redis_cache_key(cache_prefix, category=''):
    user_id = 'ANONYMOUS'
    if current_user.is_authenticated():
        user_id = current_user.string_id
    cache_key = make_template_fragment_key(cache_prefix,
        vary_on=[user_id, category])
    # Add prefix to the cache key and a *
    return '{0}{1}*'.format(app.config['CACHE_KEY_PREFIX'], cache_key)


def delete_redis_cache_keys(cache_prefix, category=''):
    key = make_redis_cache_key(cache_prefix, category)
    keys_list = redis_client.keys(key)
    for key in keys_list: redis_client.delete(key)


def delete_redis_cache_post(uuid):
    user_id = 'ANONYMOUS'
    if current_user.is_authenticated():
        user_id = current_user.string_id
    cache_key = make_template_fragment_key('post',
        vary_on=[uuid])
    # Add prefix to the cache key
    key = '{0}{1}*'.format(app.config['CACHE_KEY_PREFIX'], cache_key)
    keys_list = redis_client.keys(key)
    for key in keys_list: redis_client.delete(key)

