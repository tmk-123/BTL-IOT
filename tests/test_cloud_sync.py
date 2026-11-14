from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from cloud_sync import envelope, sync_once


class CloudSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.images = self.root / 'evidence'
        self.images.mkdir()
        image = self.images / 'test.jpg'
        image.write_bytes(b'\xff\xd8\xfffixture')
        self.event = {'event_id': 'test:1', 'raw_image': str(image), 'source': 'http://user:password@camera/capture'}
        self.database = self.root / 'traffic.db'
        with closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE events(event_id TEXT PRIMARY KEY, payload_json TEXT)')
            db.execute('INSERT INTO events VALUES (?,?)', ('test:1', json.dumps(self.event)))
            db.commit()
        self.config = dict(database=str(self.database), evidence_dir=str(self.images),
                           state=str(self.root / 'state.db'), url='https://example.com/iot-api', token='x' * 48)

    def tearDown(self):
        self.tmp.cleanup()

    def test_offline_retains_event_then_retry_acknowledges_once(self):
        before = self.database.read_bytes()
        def offline(*args):
            raise OSError('network down')
        self.assertEqual(sync_once(self.config, offline), (0, 1))
        calls = []
        self.assertEqual(sync_once(self.config, lambda *args: calls.append(args)), (1, 0))
        self.assertEqual(sync_once(self.config, lambda *args: calls.append(args)), (0, 0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.database.read_bytes(), before)

    def test_source_credentials_and_local_paths_not_exported(self):
        body = envelope(self.event, self.images)
        self.assertEqual(body['event']['source'], 'edge-camera')
        self.assertIs(body['event']['raw_image'], True)
        self.assertNotIn('password', json.dumps(body))
        self.assertNotIn(str(self.root), json.dumps(body))

    def test_missing_image_is_not_acknowledged(self):
        Path(self.event['raw_image']).unlink()
        self.assertEqual(sync_once(self.config, lambda *args: self.fail('must not upload')), (0, 1))

    def test_image_path_cannot_escape_evidence_root(self):
        self.event['raw_image'] = str(self.database)
        with self.assertRaises(ValueError):
            envelope(self.event, self.images)

    def test_acknowledgements_are_scoped_to_server(self):
        sender = lambda *args: None
        self.assertEqual(sync_once(self.config, sender), (1, 0))
        self.config['url'] = 'https://another.example.com/iot-api'
        self.assertEqual(sync_once(self.config, sender), (1, 0))

    def test_unavailable_server_stops_batch_until_next_cycle(self):
        with closing(sqlite3.connect(self.database)) as db:
            other = dict(self.event, event_id='test:2')
            db.execute('INSERT INTO events VALUES (?,?)', ('test:2', json.dumps(other)))
            db.commit()
        attempts = []
        def offline(*args):
            attempts.append(1)
            raise urllib.error.URLError('offline')
        self.assertEqual(sync_once(self.config, offline), (0, 1))
        self.assertEqual(len(attempts), 1)


if __name__ == '__main__':
    unittest.main()
