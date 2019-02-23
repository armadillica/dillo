from pillar.api.utils.authentication import force_cli_user
from pillar.api.local_auth import create_local_user

from dillo import EXTENSION_NAME

from abstract_dillo_test import AbstractDilloTest


class UserTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.proj_id, self.project = self.ensure_project_exists()
        with self.app.test_request_context():
            force_cli_user()
            self.local_user_id = create_local_user('harry@hogwarts.edu', 'password')

    def test_create_user(self):
        db_user = self.fetch_user_from_db(self.local_user_id)
        self.assertEqual('harry@hogwarts.edu', db_user['email'])
        extension_props_public = db_user['extension_props_public'][EXTENSION_NAME]
        # Ensure that followed_communities exists and is empty
        self.assertEqual([], extension_props_public['followed_communities'])

    def test_user_page(self):
        # Username 'tester' does not exist
        self.get('/u/james', expected_status=404)
        # Username will be 'harry'
        with self.app.test_request_context():
            force_cli_user()
            create_local_user('james@hogwarts.edu', 'password')
        self.get('/u/james')

    def test_follow_community_happy(self):
        self.create_valid_auth_token(self.local_user_id)
        r = self.post(f'/api/communities/follow/{self.proj_id}', expected_status=200,
                      auth_token='token').get_json()
        self.assertEqual('OK', r['_status'])

        # Ensure project was added to the list
        db_user = self.fetch_user_from_db(self.local_user_id)
        self.assertIn(self.proj_id, db_user['extension_props_public'][EXTENSION_NAME]['followed_communities'])

    def test_follow_community_non_authenticated(self):
        self.post(f'/api/communities/follow/{self.proj_id}', expected_status=403)

    def test_follow_community_non_existing_or_deleted(self):
        self.post(f'/api/communities/follow/invalid_url', expected_status=404)
        # TODO(fsiddi) create and delete a project, ensure it's not possible to follow it
