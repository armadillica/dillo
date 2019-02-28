import mock
import copy
from bson import ObjectId
from datetime import datetime, timezone
import flask
import pillar.tests.common_test_data as ctd
from abstract_dillo_test import AbstractDilloTest


class NodeOwnerTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)
        self.dillo_user_main_grp = self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.user_id = self.create_user(groups=[self.dillo_user_main_grp], token='token')
        self.project_id, _ = self.ensure_project_exists()

        self.test_node = self.create_post_document(self.project_id, self.user_id)

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


class TestPostsListing(AbstractDilloTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.dillo_user_main_grp = self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.user_id = self.create_user(user_id=ObjectId(), groups=[self.dillo_user_main_grp],
                                        token='tina-token', email='tina@ilvermorny.edu')
        self.proj_id, self.project = self.ensure_project_exists()

        # Create 3 communities
        project_urls = ['today', 'hoy', 'rcs']
        self.projects = self.create_projects(project_urls)

    def create_projects(self, project_urls: list):
        """Given a list of urls, create projects."""
        projects = []
        for url in project_urls:
            project_overrides = {'_id': ObjectId(), 'url': url}
            proj_id, project = self.ensure_project_exists(project_overrides)
            projects.append((proj_id, project))
        return projects

    def create_posts(self, user_id: ObjectId, auth_token: str, amount_per_project=3) -> list:
        """Create a number of posts in each community.

        Returns:
            An array of post Object ids.
        """

        post_ids = []

        for p in self.projects:
            for i in range(amount_per_project):
                doc = self.create_post_document(p[0], user_id, name=f"My {p[1]['url']} post {i}")
                r = self.post('/api/nodes', json=doc, auth_token=auth_token, expected_status=201)
                post_ids.append(ObjectId(r.json['_id']))

        # Set all posts properties.status to 'published'
        with self.app.app_context():
            nodes_collection = self.app.db('nodes')
            nodes_collection.update_many({'node_type': 'dillo_post'},
                                         {'$set': {'properties.status': 'published'}})

        return post_ids

    def test_followed_communities_listing(self):
        """Check that only posts from followed communities are listed."""

        # Create additional users
        user_1 = self.create_user(user_id=ObjectId(), groups=[self.dillo_user_main_grp],
                                  token='user_1-token', email='user_1@ilvermorny.edu')

        self.create_posts(user_1, auth_token='user_1-token')

        # Use the 'default' user to check the posts feed when no community is followed
        with self.app.app_context():
            self.login_api_as(self.user_id)
            r = self.get('/api/posts')
            # Ensure that 9 posts are listed
            self.assertEqual(9, r.json['metadata']['total'])

        # Set the 'default' user to follow some communities
        with self.app.app_context():
            followed_communities_k = f'extension_props_public.dillo.followed_communities'
            users_collection = self.app.db('users')
            users_collection.update_one(
                {'_id': self.user_id},
                {'$set': {followed_communities_k: [self.projects[0][0], self.projects[1][0]]}})

        # Ensure that only posts from the followed communities are visible in the feed
        with self.app.app_context():
            self.login_api_as(self.user_id)
            r = self.get('/api/posts')
            # Ensure that 6 posts are listed
            self.assertEqual(6, r.json['metadata']['total'])

    def test_pagination(self):
        self.create_posts(self.user_id, 'tina-token', amount_per_project=10)

        with self.app.app_context():
            # Query for all posts with no query arguments /api/posts
            url = flask.url_for('posts_api.get_posts')
            r = self.get(url)
            metadata = r.json['metadata']
            data = r.json['data']

            # Ensure that the first page, with PAGINATION_DEFAULT_POSTS elements
            # is being retrieved
            pagination_default = self.app.config['PAGINATION_DEFAULT_POSTS']
            self.assertEqual(30, metadata['total'])
            self.assertEqual(1, metadata['page'])
            self.assertEqual(pagination_default, len(data))

            # Query for for all posts, page 2 /api/posts?page=2
            url = flask.url_for('posts_api.get_posts', page=2)
            r = self.get(url)
            metadata = r.json['metadata']
            data = r.json['data']

            self.assertEqual(2, metadata['page'])
            self.assertEqual(pagination_default, len(data))

    def test_sorting_hot(self):
        with self.app.app_context():
            nodes_collection = self.app.db('nodes')

        post_ids = self.create_posts(self.user_id, 'tina-token', amount_per_project=10)

        with self.app.app_context():
            # Manually set the hotness of post
            for idx, post_id in enumerate(post_ids):
                nodes_collection.update_one({'_id': post_id},
                                            {'$set': {'properties.hot': idx}})

        # Query for all posts with no query arguments /api/posts
        r = self.get('/api/posts')
        data = r.json['data']

        # Ensure that results are ordered by decreasing 'properties.hot'.
        for idx, p in enumerate(data):
            following_post_idx = idx + 1
            # If we reached the last element of the array, stop
            if following_post_idx == len(data):
                continue
            following_post = data[following_post_idx]
            # Ensure that every post has has less or equal hot than the following
            self.assertGreater(p['properties']['hot'], following_post['properties']['hot'])

    def test_sorting_created(self):
        self.create_posts(self.user_id, 'tina-token', amount_per_project=10)

        # Query for all posts with no query arguments /api/posts?sorting=-new
        r = self.get('/api/posts?sorting=new')
        data = r.json['data']

        # Ensure that results are ordered by decreasing 'properties.hot'.
        for idx, p in enumerate(data):
            following_post_idx = idx + 1
            # If we reached the last element of the array, stop
            if following_post_idx == len(data):
                continue
            following_post = data[following_post_idx]
            # Ensure that every post has has less or equal creation date than the following
            # TODO(fsiddi) ensure there is enough time between creation dates
            self.assertGreaterEqual(p['_created'], following_post['_created'])
