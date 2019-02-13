import os
from pillar.tests import PillarTestServer, AbstractPillarTest

MY_PATH = os.path.dirname(os.path.abspath(__file__))


class DilloTestServer(PillarTestServer):
    def __init__(self, *args, **kwargs):
        PillarTestServer.__init__(self, *args, **kwargs)

        from dillo import DilloExtension
        self.load_extension(DilloExtension(), None)

    def _load_flask_config(self):
        super(DilloTestServer, self)._load_flask_config()

        pillar_config_file = os.path.join(MY_PATH, 'config_testing.py')
        self.config.from_pyfile(pillar_config_file)


class AbstractDilloTest(AbstractPillarTest):
    pillar_server_class = DilloTestServer

    def tearDown(self):

        self.unload_modules('dillo')

        AbstractPillarTest.tearDown(self)

    @property
    def dillo(self):
        return self.app.pillar_extensions['dillo']

    def ensure_project_exists(self, project_overrides=None):
        from dillo.setup import setup_for_dillo
        from pillar.api.utils.authentication import force_cli_user

        project_overrides_base = {
            'picture_header': None,
            'picture_square': None,
            'url': 'default-project'
        }

        if project_overrides:
            project_overrides_base.update(project_overrides)

        proj_id, project = AbstractPillarTest.ensure_project_exists(self, project_overrides_base)

        with self.app.test_request_context():
            force_cli_user()
            dillo_project = setup_for_dillo(project['url'], replace=True)

        return proj_id, dillo_project

    def create_post_document(self, project_id, user_id, name='My Post'):
        return {
            'project': project_id,
            'node_type': 'dillo_post',
            'name': name,
            'user': user_id,
            'properties': {
                'tags': ['Artwork'],
                'post_type': 'link',
            },
        }
