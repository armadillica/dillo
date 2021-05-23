from django.test import SimpleTestCase, Client, override_settings

from dillo.query import parse_text_query


class TestViewsMixin(SimpleTestCase):
    def setUp(self) -> None:
        self.filters = {}

    def test_parse_text_query_single_word(self):
        text = 'animation'
        filters = parse_text_query(text, self.filters)
        self.assertEqual({'title__search': text}, filters)

    def test_parse_text_query_multiple_words(self):
        text = 'animation tutorial'
        filters = parse_text_query(text, self.filters)
        self.assertEqual({'title__search': text}, filters)

    def test_parse_text_query_multiple_words_and_user(self):
        text = 'animation tutorial user=harry'
        filters = parse_text_query(text, self.filters)
        self.assertEqual(
            {'title__search': 'animation tutorial', 'user__username': 'harry'}, filters
        )

    def test_parse_text_query_multiple_words_and_other_query(self):
        text = 'animation tutorial other=content'
        filters = parse_text_query(text, self.filters)
        self.assertEqual({'title__search': text}, filters)

    def test_parse_text_query_only_user(self):
        text = 'user=harry'
        filters = parse_text_query(text, self.filters)
        self.assertEqual({'user__username': 'harry'}, filters)
