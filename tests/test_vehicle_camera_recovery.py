from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
import vehicle_detector
from light_state import LightState
from red_light_demo import lamp
import json


class Tensor:
    def __init__(self, value): self.value = value
    def cpu(self): return self
    def int(self): return self
    def tolist(self): return self.value


class Boxes:
    def __init__(self, bottom):
        self.xyxy = Tensor([[20, bottom-20, 60, bottom]])
        self.id, self.cls, self.conf = Tensor([1]), Tensor([0]), Tensor([.9])
    def __len__(self): return 1


class CameraRecoveryTests(unittest.TestCase):
    def test_yellow_crossing_counts_and_persists_as_suspected_with_evidence(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cap = Mock()
        observations = iter([10.6, 10.8])
        def read_observation():
            cap.observed_mono = next(observations)
            cap.observed_at = '2026-11-05T13:00:00+07:00'
            cap.discontinuity = False
            return True, frame
        cap.read.side_effect = read_observation
        model = Mock()
        model.names = {0: 'car'}
        model.track.side_effect = [[SimpleNamespace(boxes=Boxes(bottom), plot=lambda: frame.copy())]
                                  for bottom in (30, 80)]
        light = LightState()
        light.ingest(json.dumps(lamp(10, 'YELLOW')[2]), now=10)
        receiver = Mock(state=light)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root/'traffic.db'
            args = ['vehicle_detector.py', '--source', 'http://camera/capture', '--snapshot', '--async-snapshot', '--track',
                    '--no-display', '--max-frames', '2', '--line', '0', '.5', '1', '.5',
                    '--database', str(database), '--evidence-dir', str(root/'evidence'), '--output', str(root/'logs')]
            with patch.object(sys, 'argv', args), patch.object(vehicle_detector, 'YOLO', return_value=model), \
                 patch('latest_capture.LatestSnapshotCapture', return_value=cap), \
                 patch.object(vehicle_detector, 'from_arguments', return_value=receiver), \
                 patch.object(vehicle_detector.cv2, 'putText', wraps=vehicle_detector.cv2.putText) as put_text:
                self.assertEqual(vehicle_detector.main(), 0)
            connection = sqlite3.connect(database)
            try:
                rows = connection.execute('SELECT light_state,assessment,raw_image,observed_at FROM events').fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][:2], ('YELLOW', 'suspected_yellow_light'))
                self.assertTrue(Path(rows[0][2]).is_file())
                self.assertEqual(rows[0][3], '2026-11-05T13:00:00+07:00')
            finally:
                connection.close()
            captions = [call.args[1] for call in put_text.call_args_list]
            self.assertIn('Suspected red/yellow-light: 1', captions)
        receiver.stop.assert_called_once()
        cap.release.assert_called_once()

    def test_async_outage_not_delivered_as_failure_still_resets_crossing(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cap = Mock()
        observations = iter([(10, False), (11, True), (12, False)])
        def read_observation():
            cap.observed_mono, cap.discontinuity = next(observations)
            cap.observed_at = '2026-11-05T13:00:00+07:00'
            return True, frame
        cap.read.side_effect = read_observation
        model = Mock()
        model.names = {0: 'car'}
        model.track.side_effect = [[SimpleNamespace(boxes=Boxes(bottom), plot=lambda: frame.copy())]
                                  for bottom in (30, 80, 85)]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root/'traffic.db'
            args = ['vehicle_detector.py', '--source', 'http://camera/capture', '--snapshot', '--async-snapshot',
                    '--track', '--no-display', '--max-frames', '3', '--line', '0', '.5', '1', '.5',
                    '--database', str(database), '--evidence-dir', str(root/'evidence'), '--output', str(root/'logs')]
            with patch.object(sys, 'argv', args), patch.object(vehicle_detector, 'YOLO', return_value=model), \
                 patch('latest_capture.LatestSnapshotCapture', return_value=cap):
                self.assertEqual(vehicle_detector.main(), 0)
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute('SELECT count(*) FROM events').fetchone()[0], 0)
            finally:
                connection.close()
        cap.release.assert_called_once()

    def test_no_crossing_is_inferred_across_failed_camera_read(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cap = Mock()
        cap.read.side_effect = [(True, frame), (False, None), (True, frame), (True, frame)]
        model = Mock()
        model.names = {0: 'car'}
        model.track.side_effect = [[SimpleNamespace(boxes=Boxes(bottom), plot=lambda: frame.copy())]
                                  for bottom in (30, 80, 85)]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root/'traffic.db'
            args = ['vehicle_detector.py', '--source', 'http://camera/capture', '--snapshot', '--track',
                    '--simulation', '--no-display', '--max-frames', '3', '--line', '0', '.5', '1', '.5',
                    '--database', str(database), '--evidence-dir', str(root/'evidence'), '--output', str(root/'logs')]
            with patch.object(sys, 'argv', args), patch.object(vehicle_detector, 'YOLO', return_value=model), \
                 patch.object(vehicle_detector, 'SnapshotCapture', return_value=cap), \
                 patch.object(vehicle_detector.time, 'sleep'):
                self.assertEqual(vehicle_detector.main(), 0)
            connection = sqlite3.connect(database)
            try: self.assertEqual(connection.execute('SELECT count(*) FROM events').fetchone()[0], 0)
            finally: connection.close()
        cap.release.assert_called_once()


if __name__ == '__main__':
    unittest.main()
