from django.test import SimpleTestCase
from dillo.templatetags import dillo_filters


class CompactNumberTest(SimpleTestCase):
    def test_compact_numer_filter(self):
        # Define tuples of input and expected output values
        values = [
            (1, "1"),
            (10, "10"),
            (100, "100"),
            (999, "999"),
            (1250, "1.25K"),
            (1999, "2K"),
            (9999, "10K"),
            (10001, "10K"),
        ]
        for value in values:
            value_compact = dillo_filters.compact_number(value[0])
            self.assertEqual(value[1], value_compact)
