import mock
import copy
from datetime import datetime, timezone
import pillar.tests.common_test_data as ctd
from abstract_dillo_test import AbstractDilloTest


class NodeOwnerTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)
        self.dillo_user_main_grp = self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.user_id = self.create_user(groups=[self.dillo_user_main_grp])
        self.create_valid_auth_token(self.user_id, 'token')
        self.project_id, _ = self.ensure_project_exists()

        self.test_node = {
            'project': self.project_id,
            'node_type': 'dillo_post',
            'name': 'test with user',
            'user': self.user_id,
            'properties': {
                'tags': ['Artwork'],
                'post_type': 'link',
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

    def _test_user(self, test_node, auth_token='token'):
        resp = self.post('/api/nodes', json=test_node, auth_token=auth_token,
                         expected_status=201)
        created = resp.get_json()

        resp = self.get(f"/api/nodes/{created['_id']}", auth_token=auth_token)
        json_node = resp.get_json()
        self.assertEqual(str(self.user_id), json_node['user'])
        return json_node

    def test_delete_with_explicit_owner(self):
        test_node = copy.deepcopy(self.test_node)
        node_doc = self._test_user(test_node)
        # Is DELETE allowed?
        self.assertIn('DELETE', node_doc['allowed_methods'])
        # Delete the post
        self.delete(f"/api/nodes/{node_doc['_id']}", headers={'If-Match': node_doc['_etag']},
                    auth_token='token', expected_status=204)

    def test_delete_with_other_user(self):
        """Other users should not be able to delete a post."""
        other_user_id = self.create_user(
            user_id='cafef005972666988bef6500',
            groups=[self.dillo_user_main_grp])
        self.create_valid_auth_token(other_user_id, 'other_token')
        test_node = copy.deepcopy(self.test_node)
        node_doc = self._test_user(test_node)
        # Do not allow post deletion
        self.delete(f"/api/nodes/{node_doc['_id']}", headers={'If-Match': node_doc['_etag']},
                    auth_token='other_token', expected_status=403)

    @mock.patch('dillo.api.posts.hooks.algolia_index_post_save')
    def test_edit_with_explicit_owner(self, algolia_index_post_save):
        """Test editing a node as the owner of the node. We ignore the
        algolia_index_post_save call in one of the hooks.
        """
        import pillarsdk
        from pillar.web.utils import system_util

        other_user_id = self.create_user(
            user_id='cafef005972666988bef6500',
            groups=[self.dillo_user_main_grp])
        self.create_valid_auth_token(other_user_id, 'other_token')
        test_node = copy.deepcopy(self.test_node)
        node_doc = self._test_user(test_node, auth_token='other_token')
        # Is PUT allowed?
        self.assertIn('PUT', node_doc['allowed_methods'])

        with self.app.test_request_context():
            api = system_util.pillar_api(token='other_token')
            node = pillarsdk.Node.find(node_doc['_id'], api=api)
            node.properties.content = 'Some content here'
            node.properties.status = 'published'
            node.update(api=api)

    @mock.patch('dillo.api.posts.hooks.algolia_index_post_save')
    def test_edit_with_other_user(self, algolia_index_post_save):
        """Test editing a node as another user than the owner. We ignore the
        algolia_index_post_save call in one of the hooks.
        """

        from pillar.api.utils import remove_private_keys
        from pillarsdk.utils import remove_none_attributes

        other_user_id = self.create_user(
            user_id='cafef005972666988bef6500',
            groups=[self.dillo_user_main_grp])
        self.create_valid_auth_token(other_user_id, 'other_token')
        test_node = copy.deepcopy(self.test_node)
        node_doc = self._test_user(test_node, auth_token='other_token')

        # Some basic properties need to be set in order to publish correctly
        node_doc['properties']['content'] = 'Some great content'
        node_doc['properties']['status'] = 'published'

        node_doc_no_priv = remove_private_keys(node_doc)
        node_doc_no_none = remove_none_attributes(node_doc_no_priv)

        # The owner of the post can edit
        self.put(
            f"/api/nodes/{node_doc['_id']}",
            json=node_doc_no_none,
            headers={'If-Match': node_doc['_etag']},
            auth_token='other_token',
            expected_status=200)

        # Some other user tries to get the node and edit it
        resp = self.get(f"/api/nodes/{node_doc['_id']}", auth_token='token')
        node_doc = resp.get_json()
        node_doc['properties']['content'] = 'Some illegally edited content'

        node_doc_no_priv = remove_private_keys(node_doc)
        node_doc_no_none = remove_none_attributes(node_doc_no_priv)

        # Such user is not allowed
        self.put(
            f"/api/nodes/{node_doc['_id']}",
            json=node_doc_no_none,
            headers={'If-Match': node_doc['_etag']},
            auth_token='token',
            expected_status=403)


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
