"""Safe Markdown rendering for public training documentation."""

import markdown
import nh3


ALLOWED_TAGS = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2',
    'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'li', 'ol', 'p', 'pre', 'strong',
    'ul', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
}
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'code': ['class'],
    'th': ['align'],
    'td': ['align'],
}
ALLOWED_PROTOCOLS = {'http', 'https', 'mailto'}


def render_markdown(source):
    """Render common Markdown syntax and sanitize HTML/links before display."""
    rendered = markdown.markdown(
        source or '',
        extensions=['extra', 'sane_lists'],
        output_format='html',
    )
    return nh3.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_PROTOCOLS,
        strip_comments=True,
    )
