import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
import dashboard_cloud


class CloudDashboardTests(unittest.TestCase):
    def test_filter_encoding_and_legacy_row_shape(self):
        reply = {'events': [{'event_id': 'x', 'simulation': True}], 'total': 1, 'summary': {'unverified': 1}}
        with patch.object(dashboard_cloud, 'get', return_value=json.dumps(reply).encode()) as get:
            rows, total, summary = dashboard_cloud.load_cloud_events(assessment=('a', 'b'), search="%_'",
                                                                    date_from='2026-11-01', limit=25, offset=50)
        self.assertEqual(get.call_args.args[1]['assessment'], ['a', 'b'])
        self.assertEqual(get.call_args.args[1]['offset'], 50)
        self.assertEqual(get.call_args.args[1]['search'], "%_'")
        self.assertTrue(json.loads(rows[0]['payload_json'])['simulation'])
        self.assertEqual(total, 1)

    def test_image_references_cannot_escape_api(self):
        with patch.object(dashboard_cloud, 'get') as get:
            for value in ('../../secrets', 'https://evil.test/a', '/etc/passwd', 'x.jpg'):
                with self.assertRaises(ValueError):
                    dashboard_cloud.load_cloud_image(value)
            get.assert_not_called()

    def test_token_only_in_header_and_literal_query_encoding(self):
        env = {'IOT_CLOUD_URL': 'https://example.test/iot-api', 'IOT_READ_TOKEN': 'private-token'}
        with patch.dict(os.environ, env), patch.object(dashboard_cloud, 'urlopen') as opened:
            opened.return_value.__enter__.return_value.read.return_value = b'{}'
            dashboard_cloud.get('/events', {'search': '%_', 'assessment': ['a', 'b']})
        request = opened.call_args.args[0]
        self.assertNotIn('private-token', request.full_url)
        self.assertEqual(request.get_header('Authorization'), 'Bearer private-token')
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query, {'search': ['%_'], 'assessment': ['a', 'b']})

    def test_insecure_remote_configuration_is_rejected(self):
        with patch.dict(os.environ, {'IOT_CLOUD_URL': 'http://public.example', 'IOT_READ_TOKEN': 'token'}):
            with self.assertRaises(ValueError):
                dashboard_cloud.get('/events')

    def test_cloud_ui_hides_local_paths_and_handles_api_failure(self):
        from streamlit.testing.v1 import AppTest
        path = str(Path(__file__).resolve().parents[1] / 'python/dashboard.py')
        with patch.dict(os.environ, {'IOT_CLOUD_URL': 'https://example.test'}), \
                patch.object(dashboard_cloud, 'load_cloud_events', return_value=([], 0, {})):
            app = AppTest.from_file(path, default_timeout=15).run()
            self.assertFalse(app.exception)
            self.assertFalse(any(item.key == 'dataset' for item in app.selectbox))
            self.assertFalse(any(item.key == 'database' for item in app.text_input))
            self.assertEqual(app.metric[0].value, '0')
        with patch.dict(os.environ, {'IOT_CLOUD_URL': 'https://example.test'}), \
                patch.object(dashboard_cloud, 'load_cloud_events', side_effect=OSError('secret-url')):
            app = AppTest.from_file(path, default_timeout=15).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertNotIn('secret-url', app.error[0].value)


if __name__ == '__main__':
    unittest.main()
