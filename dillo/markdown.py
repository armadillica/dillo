"""Handle cleaning and rendering of markdown."""
from typing import Optional, Tuple
import re

from markupsafe import Markup
import bleach
import mistune

_markdown: Optional[mistune.Markdown] = None
SHORTCODE_WITH_LINK_PATTERN = r'{(?:media\s+|iframe\s+)\w*(?:\s*link|\s*src)=.*'


def sanitize(text: str) -> str:
    """Remove **all** HTML tags from a given text."""
    return bleach.clean(text, tags=[], attributes={}, styles=[], strip=True)


def parse_shortcode_link(self, match: re.Match, state) -> Tuple[str]:
    """Define how to parse a shortcode with link."""
    return 'shortcode_link', match.group()


def keep_shortcode_link(matched_text: str) -> str:
    """Leave shortcode link as is."""
    return matched_text


def plugin_shortcode_with_link(md):
    """Define a plugin that will keep shortcode links intact.

    This is necessary because by default mistune "urlises" (wraps into "a href") all links.
    """
    md.inline.register_rule('shortcode_link', SHORTCODE_WITH_LINK_PATTERN, parse_shortcode_link)
    md.inline.rules.append('shortcode_link')
    md.renderer.register('shortcode_link', keep_shortcode_link)


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.create_markdown(
            escape=True, plugins=[plugin_shortcode_with_link, mistune.plugins.extra.plugin_url],
        )

    return Markup(_markdown(text))
