import logging_config
from abstract_dillo_test import AbstractDilloTest


class UserTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.proj_id, self.project = self.ensure_project_exists()

    def test_create_user(self):
        from pillar.api.utils.authentication import force_cli_user
        from pillar.api.local_auth import create_local_user
        with self.app.test_request_context():
            force_cli_user()
            user_id = create_local_user('harry@hogwarts.edu', 'password')
            db_user = self.fetch_user_from_db(user_id)
            print(db_user)

    def test_user_page(self):
        from pillar.api.utils.authentication import force_cli_user
        from pillar.api.local_auth import create_local_user
        # Username 'tester' does not exist
        self.get('/u/harry', expected_status=404)
        # Username will be 'harry'
        with self.app.test_request_context():
            force_cli_user()
            create_local_user('harry@hogwarts.edu', 'password')
        self.get('/u/harry')
