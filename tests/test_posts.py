import json
import pillar.tests.common_test_data as ctd
from abstract_dillo_test import AbstractDilloTest


class NodeOwnerTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)
        self.user_id = self.create_user()
        self.create_valid_auth_token(self.user_id, 'token')
        self.project_id, _ = self.ensure_project_exists(
            project_overrides={'permissions': {
                'users': [
                    {'user': self.user_id,
                     'methods': ['GET', 'PUT', 'POST', 'DELETE']}
                ],
            }}
        )
        # self.project_id, _ = self.ensure_project_exists()

    def test_create_with_explicit_owner(self):
        test_node = {
            'project': self.project_id,
            'node_type': 'dillo_post',
            'name': 'test with user',
            'user': self.user_id,
            'properties': {
                'category': 'Fün'
            },
        }
        self._test_user(test_node)

    def test_create_with_implicit_owner(self):
        test_node = {
            'project': self.project_id,
            'node_type': 'dillo_post',
            'name': 'test with user',
            'properties': {
                'category': 'Fün'
            },
        }
        self._test_user(test_node)

    def _test_user(self, test_node):
        resp = self.post('/api/nodes', json=test_node, auth_token='token',
                         expected_status=201)
        created = resp.get_json()

        resp = self.get(f"/api/nodes/{created['_id']}", auth_token='token')
        json_node = resp.get_json()
        self.assertEqual(str(self.user_id), json_node['user'])
