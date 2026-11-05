from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from plate_autosave import PlateAutoSaver
from plate_scanner import save_result


@dataclass
class Box:
    x1: int = 10
    y1: int = 10
    x2: int = 50
    y2: int = 30


@dataclass
class Detection:
    bounding_box: Box


@dataclass
class Result:
    detection: Detection
    ocr: object = None


def track(identity=1, stable=None):
    return dict(track_id=identity, stable_text=stable, raw_text=stable, status='consensus' if stable else 'pending')


class AutoSaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / 'plates'
        self.saver = PlateAutoSaver(self.output, 'http://camera/capture', save_result)
        self.frame = np.zeros((60, 80, 3), dtype=np.uint8)
        self.result = Result(Detection(Box()))

    def tearDown(self):
        self.temp.cleanup()

    def update(self, tracks):
        return self.saver.update(self.frame, self.frame, [self.result] * len(tracks), tracks)

    def test_no_plate_does_not_create_files(self):
        self.assertEqual(self.update([]), [])
        self.assertFalse(self.output.exists())

    def test_pending_detection_is_saved_without_keypress_once(self):
        folders = self.update([track()])
        for _ in range(20): self.assertEqual(self.update([track()]), [])
        self.assertEqual(len(list(self.output.iterdir())), 1)
        folder = folders[0]
        for name in ('frame.jpg', 'annotated.jpg', 'plate_0.jpg', 'result.json', 'event.json'):
            self.assertTrue((folder / name).is_file())
        crop = cv2.imdecode(np.fromfile(str(folder/'plate_0.jpg'), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(crop.shape[:2], (20, 40))
        self.assertEqual(json.loads((folder/'event.json').read_text())['status'], 'detected')

    def test_consensus_snapshot_is_grouped_and_does_not_overwrite_detection(self):
        folder = self.update([track()])[0]
        first = (folder/'result.json').read_bytes()
        saved = self.update([track(stable='80441NN02')])
        self.assertEqual(saved, [folder/'confirmed'])
        for _ in range(20): self.assertEqual(self.update([track(stable='80441NN02')]), [])
        self.assertEqual((folder/'result.json').read_bytes(), first)
        event = json.loads((folder/'event.json').read_text())
        self.assertEqual(event['stable_text'], '80441NN02')
        self.assertTrue((folder/event['confirmed_result']).is_file())
        # Later OCR disagreement must not relabel the already saved confirmed snapshot.
        self.update([track(stable='80441NN03')])
        self.assertEqual(json.loads((folder/'event.json').read_text())['stable_text'], '80441NN02')

    def test_simultaneous_tracks_get_separate_folders(self):
        folders = self.update([track(1), track(2)])
        self.assertEqual(len(set(folders)), 2)
        for folder in folders:
            self.assertEqual(len(json.loads((folder/'result.json').read_text())['results']), 1)

    def test_failed_save_is_not_reported_as_saved(self):
        save = Mock(side_effect=OSError('Disk full'))
        saver = PlateAutoSaver(self.output, 'camera', save)
        with self.assertRaises(OSError):
            saver.update(self.frame, self.frame, [self.result], [track()])
        self.assertEqual(saver.entries, {})


if __name__ == '__main__':
    unittest.main()
