import pytz
from datetime import datetime
from django.test import SimpleTestCase


class TestSorting(SimpleTestCase):
    def test_hotness(self):
        """We expect the sorted values to reflect the original order in the list."""
        from dillo.models.sorting import compute_hotness

        t = datetime(2017, 2, 11, 0, 0, 0, 0, pytz.UTC)
        y = datetime(2017, 2, 10, 0, 0, 0, 0, pytz.UTC)
        w = datetime(2017, 2, 5, 0, 0, 0, 0, pytz.UTC)
        cases = [
            (compute_hotness(1, 8, t), 'today super bad'),
            (compute_hotness(0, 3, t), 'today slightly worse'),
            (compute_hotness(0, 2, y), 'yesterday bad'),
            (compute_hotness(0, 2, t), 'today bad'),
            (compute_hotness(4, 4, w), 'last week controversial'),
            (compute_hotness(7, 1, w), 'last week very good'),
            (compute_hotness(5, 1, y), 'yesterday medium'),
            (compute_hotness(5, 0, y), 'yesterday good'),
            (compute_hotness(7, 1, y), 'yesterday very good'),
            (compute_hotness(4, 4, t), 'today controversial'),
            (compute_hotness(7, 1, t), 'today very good'),
        ]
        sorted_by_hot = sorted(cases, key=lambda tup: tup[0])
        for idx, t in enumerate(sorted_by_hot):
            self.assertEqual(cases[idx][0], t[0])
