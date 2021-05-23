def parse_text_query(text: str, filters: dict):
    """Extend query filters by parsing text.

    If a test looks like user=harry, add it as a dedicated filter to the
    filters dictionary.
    """
    text_filter = ''
    for t in text.split():
        if t.startswith('user='):
            filters['user__username'] = t.split('=')[1]
        else:
            text_filter = f"{text_filter} {t}"
    if text_filter:
        filters['title__search'] = text_filter.strip()
    return filters
