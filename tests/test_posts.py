from datetime import datetime, timezone
import copy
import pillar.tests.common_test_data as ctd
from abstract_dillo_test import AbstractDilloTest


class NodeOwnerTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)
        dillo_user_main_grp = self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.user_id = self.create_user(groups=[dillo_user_main_grp])
        self.create_valid_auth_token(self.user_id, 'token')
        self.project_id, _ = self.ensure_project_exists()

        self.test_node = {
            'project': self.project_id,
            'node_type': 'dillo_post',
            'name': 'test with user',
            'user': self.user_id,
            'properties': {
                'tags': ['Fün']
            },
        }

    def test_create_with_explicit_owner(self):
        test_node = copy.deepcopy(self.test_node)
        self._test_user(test_node)

    def test_create_with_implicit_owner(self):
        test_node = copy.deepcopy(self.test_node)
        del(test_node['user'])
        self._test_user(test_node)

    def test_create_with_non_main_user(self):
        non_main_user_id = self.create_user(user_id='cafef005972666988bef660f')
        test_node = copy.deepcopy(self.test_node)
        self.create_valid_auth_token(non_main_user_id, 'non_main_token')
        test_node['user'] = non_main_user_id
        self.post('/api/nodes', json=test_node, auth_token='non_main_token', expected_status=403)

    def _test_user(self, test_node):
        resp = self.post('/api/nodes', json=test_node, auth_token='token',
                         expected_status=201)
        created = resp.get_json()

        resp = self.get(f"/api/nodes/{created['_id']}", auth_token='token')
        json_node = resp.get_json()
        self.assertEqual(str(self.user_id), json_node['user'])


class TestSorting(AbstractDilloTest):
    def test_hotness(self):
        """We expect the sorted values to reflect the original order in the
        list.
        """
        from dillo.utils.sorting import hot
        t = datetime(2017, 2, 11, 0, 0, 0, 0, timezone.utc)
        y = datetime(2017, 2, 10, 0, 0, 0, 0, timezone.utc)
        w = datetime(2017, 2, 5, 0, 0, 0, 0, timezone.utc)
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
