import pytz
from datetime import datetime
from django.test import SimpleTestCase


class TestSorting(SimpleTestCase):
    def test_hotness(self):
        """We expect the sorted values to reflect the original order in the list.
        """
        from dillo.models.sorting import hot

        t = datetime(2017, 2, 11, 0, 0, 0, 0, pytz.UTC)
        y = datetime(2017, 2, 10, 0, 0, 0, 0, pytz.UTC)
        w = datetime(2017, 2, 5, 0, 0, 0, 0, pytz.UTC)
        cases = [
            (hot(1, 8, t), 'today super bad'),
            (hot(0, 3, t), 'today slightly worse'),
            (hot(0, 2, y), 'yesterday bad'),
            (hot(0, 2, t), 'today bad'),
            (hot(4, 4, w), 'last week controversial'),
            (hot(7, 1, w), 'last week very good'),
            (hot(5, 1, y), 'yesterday medium'),
            (hot(5, 0, y), 'yesterday good'),
            (hot(7, 1, y), 'yesterday very good'),
            (hot(4, 4, t), 'today controversial'),
            (hot(7, 1, t), 'today very good'),
        ]
        sorted_by_hot = sorted(cases, key=lambda tup: tup[0])
        for idx, t in enumerate(sorted_by_hot):
            self.assertEqual(cases[idx][0], t[0])
