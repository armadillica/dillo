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

# Regex to look for <kbd> tags, such as [[ctrl+X]]
KBD_TAG_PATTERN = (
    r'\[\['        # [[
    r'([\s\S]+?)'  # Text
    r'\]\](?!\])'  # ]]
)

def parse_html_kbd(inline, m, state):
    text = m.group(1)
    return 'kbd', text

def render_html_kbd(keyt):
    return f'<kbd>{keyt}</kbd>'

def plugin_html_kbd(md):
    """Define a plugin that converts [[key]] to <kbd>key</kbd>."""
    md.inline.register_rule('kbd', KBD_TAG_PATTERN, parse_html_kbd)
    md.inline.rules.append('kbd')
    md.renderer.register('kbd', render_html_kbd)


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.create_markdown(
            escape=True, plugins=[
                plugin_shortcode_with_link,
                mistune.plugins.extra.plugin_url,
                plugin_html_kbd,
                'strikethrough',
                'table']
        )

    return Markup(_markdown(text))
