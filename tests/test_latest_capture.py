from pathlib import Path
import queue
import sys
import threading
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from latest_capture import LatestSnapshotCapture


class ControlledCapture:
    def __init__(self):
        self.requests = queue.Queue()
        self.replies = queue.Queue()
        self.released = False

    def read(self):
        self.requests.put(True)
        return self.replies.get(timeout=5)

    def release(self):
        self.released = True
        self.replies.put((False, None))


class LatestCaptureTests(unittest.TestCase):
    def test_discards_old_frames_and_waits_for_a_new_observation(self):
        source = ControlledCapture()
        capture = LatestSnapshotCapture('http://camera/capture', capture=source)
        try:
            source.requests.get(timeout=2)
            source.replies.put((True, np.full((2, 2, 3), 1)))
            source.requests.get(timeout=2)
            source.replies.put((True, np.full((2, 2, 3), 2)))
            source.requests.get(timeout=2)
            ok, frame = capture.read()
            self.assertTrue(ok)
            self.assertEqual(frame[0, 0, 0], 2)
            self.assertIsInstance(capture.observed_mono, float)
            self.assertIn('T', capture.observed_at)
            self.assertFalse(capture.discontinuity)
            delivered = threading.Event()
            result = []
            def consume():
                result.append(capture.read())
                delivered.set()
            consumer = threading.Thread(target=consume)
            consumer.start()
            self.assertFalse(delivered.wait(.05))
            source.replies.put((True, np.full((2, 2, 3), 3)))
            self.assertTrue(delivered.wait(2))
            consumer.join(timeout=2)
            self.assertEqual(result[0][1][0, 0, 0], 3)
        finally:
            capture.release()
        self.assertTrue(source.released)
        self.assertFalse(capture.worker.is_alive())

    def test_recovery_keeps_gap_even_when_the_failure_frame_was_dropped(self):
        source = ControlledCapture()
        capture = LatestSnapshotCapture('http://camera/capture', capture=source)
        try:
            source.requests.get(timeout=2)
            source.replies.put((False, None))
            source.requests.get(timeout=2)
            source.replies.put((True, np.zeros((2, 2, 3))))
            source.requests.get(timeout=2)
            ok, _ = capture.read()
            self.assertTrue(ok)
            self.assertTrue(capture.discontinuity)
            source.replies.put((True, np.ones((2, 2, 3))))
            source.requests.get(timeout=2)
            capture.read()
            self.assertFalse(capture.discontinuity)
        finally:
            capture.release()

    def test_persistent_failures_stop_worker_and_return_failure(self):
        source = ControlledCapture()
        capture = LatestSnapshotCapture('http://camera/capture', capture=source)
        try:
            for _ in range(3):
                source.requests.get(timeout=2)
                source.replies.put((False, None))
            capture.worker.join(timeout=2)
            self.assertFalse(capture.worker.is_alive())
            self.assertEqual(capture.read(), (False, None))
            self.assertEqual(capture.read(), (False, None))
        finally:
            capture.release()


if __name__ == '__main__':
    unittest.main()
