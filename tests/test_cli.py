import copy

from pillar.tests import common_test_data as ctd
from abstract_dillo_test import AbstractDilloTest


class TestAdditionalProps(AbstractDilloTest):
    def setUp(self, **kwargs):
        AbstractDilloTest.setUp(self, **kwargs)
        self.ensure_group_exists(
            'cafef005972666988bef650f', 'dillo_user_main')
        self.user_id = self.create_user(
            user_id=ctd.EXAMPLE_PROJECT_OWNER_ID,
            groups=[ctd.EXAMPLE_ADMIN_GROUP_ID])
        self.create_valid_auth_token(ctd.EXAMPLE_PROJECT_OWNER_ID, 'token')
        self.project_id, _ = self.ensure_project_exists()

    def attach_additional_properties(self, project_url='default-project'):
        """Given a project_url attach additional props.

        Returns a tuple with the dillo_post node_type schema before and after
        running the cli command attach_post_additional_properties.
        """
        with self.app.app_context():
            from dillo.cli import attach_post_additional_properties
            proj_coll = self.app.data.driver.db['projects']
            project = proj_coll.find_one({'_id': self.project_id})
            # Get the dillo_post_node type from the project
            dillo_post_node_type = next((nt for nt in project['node_types']
                                         if nt['name'] == 'dillo_post'), None)
            dillo_post_node_type_original = copy.deepcopy(dillo_post_node_type)
            # Try to attach an empty POST_ADDITIONAL_PROPERTIES to default-project
            attach_post_additional_properties()
            # Query for the project once more, since it might have updated
            project = proj_coll.find_one({'_id': self.project_id})
            dillo_post_node_type = next((nt for nt in project['node_types']
                                         if nt['name'] == 'dillo_post'), None)
            return dillo_post_node_type_original, dillo_post_node_type

    def test_add_props_empty(self):
        self.app.config['POST_ADDITIONAL_PROPERTIES'] = {}
        dillo_post_node_type_original, dillo_post_node_type = self.attach_additional_properties()
        # No change in the schema of dillo_post is expected
        self.assertEqual(dillo_post_node_type_original, dillo_post_node_type)

    def test_add_props(self):
        post_additional_properties = {
            'status_dev': {
                'schema':  {
                    'type': 'string',
                    'default': 'Unknown',
                    'allowed': ['Unknown', 'In Development']
                },
                'indexing': {
                    'searchable': True,
                    'faceting': 'searchable'
                },
                'projects': ['default-project'],
                'label': 'Dev. Status',
            }
        }
        self.app.config['POST_ADDITIONAL_PROPERTIES'] = post_additional_properties
        dillo_post_node_type_original, dillo_post_node_type = self.attach_additional_properties()
        # We expect the content of POST_ADDITIONAL_PROPERTIES to be in
        # dillo_post_node_type
        for k, v in post_additional_properties.items():
            self.assertNotIn(k, dillo_post_node_type_original['dyn_schema'])
            self.assertIn(k, dillo_post_node_type['dyn_schema'])
