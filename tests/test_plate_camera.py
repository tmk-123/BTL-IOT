from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from plate_scanner import LiveCamera


class FakeCapture:
    def __init__(self, recover):
        self.calls = 0
        self.recover = recover
        self.released = False

    def read(self):
        self.calls += 1
        if self.recover and self.calls > 2:
            return True, np.zeros((10, 20, 3), dtype=np.uint8)
        return False, None

    def release(self):
        self.released = True


class CameraRetryTests(unittest.TestCase):
    def test_transient_failure_recovers_and_can_close(self):
        capture = FakeCapture(True)
        with patch('plate_scanner.SnapshotCapture', return_value=capture):
            camera = LiveCamera('http://camera/capture', snapshot=True)
            try:
                frame = camera.frames.get(timeout=3)
                self.assertEqual(frame.shape, (10, 20, 3))
                self.assertIsNone(camera.error)
                self.assertEqual(camera.failures, 0)
            finally:
                camera.close()
            self.assertTrue(capture.released)

    def test_persistent_failure_stops_and_releases_capture(self):
        capture = FakeCapture(False)
        with patch('plate_scanner.SnapshotCapture', return_value=capture):
            camera = LiveCamera('http://camera/capture', snapshot=True)
            camera.thread.join(timeout=3)
            self.assertIsNotNone(camera.error)
            self.assertTrue(capture.released)
            self.assertEqual(capture.calls, 3)
            camera.close()


if __name__ == '__main__':
    unittest.main()
