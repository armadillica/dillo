from pillar.tests import PillarTestServer, AbstractPillarTest


class DilloTestServer(PillarTestServer):
    def __init__(self, *args, **kwargs):
        PillarTestServer.__init__(self, *args, **kwargs)

        from dillo import DilloExtension
        self.load_extension(DilloExtension(), None)


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

        project_overrides = dict(
            picture_header=None,
            picture_square=None,
            **(project_overrides or {})
        )
        proj_id, project = AbstractPillarTest.ensure_project_exists(self, project_overrides)

        with self.app.test_request_context():
            dillo_project = setup_for_dillo(project['url'], replace=True)

        return proj_id, dillo_project
