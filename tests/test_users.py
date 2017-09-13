import logging_config
from abstract_dillo_test import AbstractDilloTest


class UserTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.proj_id, self.project = self.ensure_project_exists()

    def test_user_page(self):
        # Username 'tester' does not exist
        self.get('/u/tester', expected_status=404)

        # Username will be 'tester'
        self.create_user()

        self.get('/u/tester')
