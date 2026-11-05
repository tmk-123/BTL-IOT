from dataclasses import dataclass
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from vehicle_plate import VehiclePlateReader


@dataclass
class Box:
    x1: int = 20
    y1: int = 60
    x2: int = 80
    y2: int = 80


@dataclass
class Detection:
    bounding_box: Box


@dataclass
class OCR:
    text: str = '30A33918'
    confidence: float = 0.99


@dataclass
class Result:
    detection: Detection
    ocr: OCR


class Model:
    def __init__(self):
        self.results = [Result(Detection(Box()), OCR())]
    def predict(self, frame):
        return self.results


class VehiclePlateTests(unittest.TestCase):
    def setUp(self):
        self.model = Model()
        self.reader = VehiclePlateReader(self.model)
        self.vehicle = dict(track_id=7, bbox=[0, 0, 100, 100])

    def test_consensus_belongs_to_vehicle_id(self):
        for index in range(5):
            result = self.reader.update(None, [self.vehicle], index/30)[7]
        self.assertEqual(result['plate_text'], '30A33918')
        self.assertEqual(result['plate_status'], 'consensus')
        self.assertEqual(result['plate_bbox'], [20, 60, 80, 80])
        other = dict(self.vehicle, track_id=8)
        self.assertIsNone(self.reader.update(None, [other], 0.2)[8]['plate_text'])

    def test_overlapping_vehicles_are_ambiguous_and_reset_votes(self):
        for index in range(5): self.reader.update(None, [self.vehicle], index/30)
        other = dict(self.vehicle, track_id=8)
        rows = self.reader.update(None, [self.vehicle, other], .2)
        self.assertTrue(all(row['plate_status']=='ambiguous' for row in rows.values()))
        self.assertIsNone(self.reader.update(None, [self.vehicle], .25)[7]['plate_text'])

    def test_multiple_plates_in_one_vehicle_are_ambiguous(self):
        self.model.results *= 2
        result = self.reader.update(None, [self.vehicle], 0)[7]
        self.assertEqual(result['plate_status'], 'ambiguous')
        self.assertIsNone(result['plate_text'])

    def test_unrelated_plate_and_expired_id_cannot_inherit_text(self):
        for index in range(5): self.reader.update(None, [self.vehicle], index/30)
        self.reader.update(None, [], 1)
        result = self.reader.update(None, [self.vehicle], 1.1)[7]
        self.assertIsNone(result['plate_text'])
        distant = dict(self.vehicle, bbox=[300, 300, 400, 400])
        result = self.reader.update(None, [distant], 1.2)[7]
        self.assertEqual(result['plate_status'], 'no_plate')

    def test_no_current_detection_does_not_return_historical_consensus(self):
        for index in range(5): self.reader.update(None, [self.vehicle], index/30)
        self.model.results = []
        result = self.reader.update(None, [self.vehicle], .2)[7]
        self.assertEqual(result['plate_status'], 'no_plate')
        self.assertIsNone(result['plate_text'])

    def test_scene_ocr_works_without_vehicle_but_is_not_assigned_to_new_id(self):
        for index in range(5):
            self.assertEqual(self.reader.update(None, [], index/30), {})
        self.assertEqual(self.reader.scene_tracks[0]['stable_text'], '30A33918')
        # Display consensus cannot be inherited by a newly detected vehicle.
        result = self.reader.update(None, [self.vehicle], .2)[7]
        self.assertIsNone(result['plate_text'])
        self.reader.reset()
        self.assertEqual(self.reader.scene_tracks, [])
        self.reader.update(None, [], .3)
        self.assertIsNone(self.reader.scene_tracks[0]['stable_text'])


if __name__ == '__main__':
    unittest.main()
