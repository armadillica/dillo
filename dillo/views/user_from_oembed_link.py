import logging
from django.http import Http404, JsonResponse
import youtube_dl
from typing import TypedDict


log = logging.getLogger(__name__)


class Profile(TypedDict):
    username: str
    url_profile: str
    url_content: str
    fullname: str
    extractor: str
    extractor_key: str


def user_from_oembed_link(request):
    try:
        url = request.GET['postContentUrl']
    except KeyError:
        raise Http404("No url specified")

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'dump_single_json': True,
        'logger': log,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        profile = Profile(
            username=info['uploader_id'],
            url_profile=info['uploader_url'],
            fullname=info['uploader'],
            extractor=info['extractor'],
            extractor_key=info['extractor_key'],
            url_content=info['webpage_url'],
        )

    return JsonResponse({**profile})
