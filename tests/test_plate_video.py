"""Exercise real video decoding/writing without downloading models."""

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from plate_scanner import scan_video


class EmptyModel:
    def draw_predictions(self, frame):
        return SimpleNamespace(image=frame, results=[])


class VideoOutputTests(unittest.TestCase):
    def test_file_timing_and_empty_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "input.avi"
            writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
            self.assertTrue(writer.isOpened())
            for value in (0, 50, 100, 150):
                writer.write(np.full((48, 64, 3), value, dtype=np.uint8))
            writer.release()
            for limit, expected in ((0, 4), (2, 2)):
                target = scan_video(EmptyModel(), source, root / "results", limit)
                summary = json.loads((target / "summary.json").read_text())
                self.assertEqual(summary["frames_processed"], expected)
                self.assertEqual(summary["frames_with_plates"], 0)
                rows = [json.loads(line) for line in (target / "frames.jsonl").read_text().splitlines()]
                self.assertEqual(len(rows), expected)
                self.assertAlmostEqual(rows[-1]["video_seconds"], (expected - 1) / 10)
                cap = cv2.VideoCapture(str(target / "annotated.mp4"))
                self.assertTrue(cap.isOpened())
                decoded = 0
                while cap.read()[0]:
                    decoded += 1
                self.assertEqual(decoded, expected)
                self.assertAlmostEqual(cap.get(cv2.CAP_PROP_FPS), 10)
                cap.release()

    def test_missing_or_unreadable_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(OSError):
                scan_video(EmptyModel(), root / "missing.mp4", root / "results")
            broken = root / "broken.mp4"
            broken.write_bytes(b"not a video")
            with self.assertRaises(OSError):
                scan_video(EmptyModel(), broken, root / "results")


if __name__ == "__main__":
    unittest.main()
