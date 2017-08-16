# -*- coding=utf-8 -*-

import logging_config
from abstract_dillo_test import AbstractDilloTest


class UserTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)

        self.proj_id, self.project = self.ensure_project_exists()

    def test_user_page(self):
        # Username 'tester' does not exist
        with self.client as c:
            r = c.get('/u/tester')
            self.assertEqual(r.status_code, 404)

        # Username will be 'tester'
        self.create_user()

        with self.client as c:
            r = c.get('/u/tester')
            self.assertEqual(r.status_code, 200)
