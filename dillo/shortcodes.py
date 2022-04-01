"""Shortcode rendering.

Shortcodes are little snippets between curly brackets, which can be rendered
into HTML. Markdown passes such snippets unchanged to its HTML output, so this
module assumes its input is HTML-with-shortcodes.

See mulholland.xyz/docs/shortcodes/.

{iframe src='http://hey' group='subscriber' nogroup='Please subscribe to view this content'}

NOTE: nested braces fail, so something like {shortcode abc='{}'} is not
supported.

NOTE: only single-line shortcodes are supported for now, due to the need to
pass them though Markdown unscathed.

NOTE: The reason this is not implemented as a markdown plugin is that
shortcodes are often applied after markdown has been rendered and stored as HTML.
"""
import html as html_module  # I want to be able to use the name 'html' in local scope.
import logging
import re
import typing
import urllib.parse
import shortcodes
from django.template.loader import render_to_string

from dillo.models.static_assets import StaticAsset

_parser: shortcodes.Parser = None
_commented_parser: shortcodes.Parser = None
log = logging.getLogger(__name__)


def shortcode(name: str):
    """Class decorator for shortcodes."""

    def decorator(decorated):
        assert hasattr(decorated, '__call__'), '@shortcode should be used on callables.'
        if isinstance(decorated, type):
            as_callable = decorated()
        else:
            as_callable = decorated
        shortcodes.register(name)(as_callable)
        return decorated

    return decorator


@shortcode('test')
class Test:
    # noqa: D101
    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Just for testing.

        "{test abc='def'}" → "<dl><dt>test</dt><dt>abc</dt><dd>def</dd></dl>"
        """
        parts = ['<dl><dt>test</dt>']

        e = html_module.escape
        parts.extend([f'<dt>{e(key)}</dt><dd>{e(value)}</dd>' for key, value in kwargs.items()])
        parts.append('</dl>')
        return ''.join(parts)


@shortcode('youtube')
class YouTube:
    # noqa: D101
    log = log.getChild('YouTube')

    def video_id(self, url: str) -> str:
        """Find the video ID from a YouTube URL.

        :raise ValueError: when the ID cannot be determined.
        """
        if re.fullmatch(r'[a-zA-Z0-9_\-]+', url):
            return url

        try:
            parts = urllib.parse.urlparse(url)
            if parts.netloc == 'youtu.be':
                return parts.path.split('/')[1]
            if parts.netloc in {'www.youtube.com', 'youtube.com'}:
                if parts.path.startswith('/embed/'):
                    return parts.path.split('/')[2]
                if parts.path.startswith('/watch'):
                    qs = urllib.parse.parse_qs(parts.query)
                    return qs['v'][0]
        except (ValueError, IndexError, KeyError):
            pass

        raise ValueError(f'Unable to parse YouTube URL {url!r}')

    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Embed a YouTube video.

        The first parameter must be the YouTube video ID or URL. The width and
        height can be passed in the equally named keyword arguments.
        """
        width = kwargs.get('width', '560')
        height = kwargs.get('height', '315')

        # Figure out the embed URL for the video.
        try:
            youtube_src = pargs[0]
        except IndexError:
            return html_module.escape('{youtube missing YouTube ID/URL}')

        try:
            youtube_id = self.video_id(youtube_src)
        except ValueError as ex:
            return html_module.escape('{youtube %s}' % "; ".join(ex.args))
        except Exception:
            return html_module.escape('{youtube missing YouTube ID/URL}')
        if not youtube_id:
            return html_module.escape('{youtube invalid YouTube ID/URL}')

        src = f'https://www.youtube.com/embed/{youtube_id}?rel=0'
        html = (
            f'<div class="video-embed-container">'
            f'<iframe class="shortcode youtube"'
            f' width="{width}" height="{height}" src="{src}"'
            f' frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>'
            f'</div>'
        )
        return html


@shortcode('media')
class Media:
    # noqa: D101

    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Handle attachment shortcode."""
        try:
            slug = pargs[0]
        except KeyError:
            return '{attachment No slug given}'

        try:
            attachment = StaticAsset.objects.get(hash_id=slug)
        except StaticAsset.DoesNotExist:
            return html_module.escape('{attachment %r does not exist}' % slug)

        return self.render(attachment, pargs, kwargs)

    def render(
        self, media: StaticAsset, pargs: typing.List[str], kwargs: typing.Dict[str, str],
    ) -> str:
        """Render attachment."""
        file_renderers = {
            'image': self.render_image,
            'video': self.render_video,
        }
        return file_renderers[media.source_type](media, pargs, kwargs)

    def render_image(
        self, media: StaticAsset, pargs: typing.List[str], kwargs: typing.Dict[str, str],
    ):
        """Render an image file."""
        if 'link' in pargs:
            kwargs['link'] = 'self'
        link = None if 'link' not in kwargs else kwargs['link']
        return render_to_string(
            'dillo/components/media_embeds/file_image.pug',
            {'media': media, 'link': link, 'class': kwargs.get('class')},
        )

    def render_video(
        self, media: StaticAsset, pargs: typing.List[str], kwargs: typing.Dict[str, str],
    ):
        """Render a video file."""
        # TODO(fsiddi) Handle processing video
        is_processing = media.video.encoding_job_status != 'job.completed'
        # TODO(fsiddi) Support looping and other options

        return render_to_string(
            'dillo/components/media_embeds/file_video.pug',
            {'media': media, 'is_processing': is_processing},
        )


class SilentParser(shortcodes.Parser):
    """Silence InvalidTagError and other exceptions shortcodes.Parser raises.

    "shortcodes.Parser" raises unhandled exceptions when it meets something
    that looks like a shortcode but doesn't not have a registered handler.
    Instead, it should ignore these occurrences and keep them as-is,
    and this monkeypatches the parser to do just that.

    Ideally, this should be fixed in the "shortcodes" module, however
    latest "shortcodes==3.0.0" is not compatible with this implementation,
    and ain't nobody got time for both figuring out why and making sure it handles its exceptions.
    """

    def _parse_token(self, token, stack, *args, **kwargs):
        try:
            super()._parse_token(token, stack, *args, **kwargs)
        except Exception:
            # Just leave it as it is.
            stack[-1].children.append(shortcodes.Text(token))


def _get_parser() -> typing.Tuple[shortcodes.Parser, shortcodes.Parser]:
    """Return the shortcodes parser, create it if necessary."""
    global _parser
    if _parser is None:
        start, end = '{}'
        _parser = SilentParser(start, end)
    return _parser


def render(text: str, context: typing.Any = None) -> str:
    """Parse and render shortcodes."""
    parser = _get_parser()

    try:
        return parser.parse(text, context)
    except shortcodes.ShortcodeError:
        log.exception('Error rendering tag')
        return text
