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
