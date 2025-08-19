from unittest import TestCase
from fastapi.testclient import TestClient
from pg.app.application import create_application


class TestBaseEventHandler(TestCase):
    def test_startup_handler(self):
        app = create_application()
        with self.assertLogs('pg', level='INFO') as cm:

            with TestClient(app):
                pass
            self.assertEqual(cm.output,
                             ['INFO:pg:Starting up ...',
                              'INFO:pg:Shutting down ...'])
