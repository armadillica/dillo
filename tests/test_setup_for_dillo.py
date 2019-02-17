import pillar.tests.common_test_data as ctd
from abstract_dillo_test import AbstractDilloTest


class SetupForDilloTest(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)
        self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.user_id = self.create_user(
            user_id=ctd.EXAMPLE_PROJECT_OWNER_ID,
            groups=[ctd.EXAMPLE_ADMIN_GROUP_ID])
        self.create_valid_auth_token(ctd.EXAMPLE_PROJECT_OWNER_ID, 'token')
        self.project_id, _ = self.ensure_project_exists()

    def test_custom_properties(self):
        """Projects should get their properties dict."""

        with self.app.test_request_context():
            proj_coll = self.app.data.driver.db['projects']
            project = proj_coll.find_one({'_id': self.project_id})
            aprops = project['extension_props']['dillo']
            self.assertIsInstance(aprops, dict)
            self.assertIsInstance(aprops['last_used_shortcodes'], dict)

    def test_saving_api(self):
        """Ensures that Eve accepts an Dillo project as valid."""

        import pillar.api.utils

        url = '/api/projects/%s' % self.project_id
        resp = self.get(url)
        proj = resp.json

        put_proj = pillar.api.utils.remove_private_keys(proj)

        self.put(url,
                 json=put_proj,
                 auth_token='token',
                 headers={'If-Match': proj['_etag']})

