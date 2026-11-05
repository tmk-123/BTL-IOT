from dataclasses import dataclass
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from plate_detection import predict_with_vehicle_crops


@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class Detection:
    bounding_box: Box


@dataclass
class Plate:
    detection: Detection
    ocr: str = '29A22222'


class CropTests(unittest.TestCase):
    def test_crop_results_map_back_without_mutating_model_result(self):
        plate = Plate(Detection(Box(10, 20, 40, 35)))
        model = Mock()
        model.predict.side_effect = [[], [plate]]
        frame = np.zeros((150, 200, 3), dtype=np.uint8)
        found = predict_with_vehicle_crops(model, frame, [[50, 60, 150, 140]])
        self.assertEqual(found[0].detection.bounding_box, Box(60, 80, 90, 95))
        self.assertEqual(plate.detection.bounding_box, Box(10, 20, 40, 35))
        self.assertEqual(model.predict.call_args_list[1].args[0].shape, (80, 100, 3))

    def test_existing_plate_skips_crop_and_overlapping_vehicles_do_not_duplicate(self):
        plate = Plate(Detection(Box(20, 20, 40, 35)))
        model = Mock()
        model.predict.side_effect = [[], [plate]]
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        found = predict_with_vehicle_crops(model, frame, [[0, 0, 90, 90], [0, 0, 95, 95]])
        self.assertEqual(len(found), 1)
        self.assertEqual(model.predict.call_count, 2)
        model.predict.reset_mock(side_effect=True)
        model.predict.return_value = [plate]
        self.assertEqual(predict_with_vehicle_crops(model, frame, [[0, 0, 90, 90]]), [plate])
        self.assertEqual(model.predict.call_count, 1)

    def test_clipping_and_invalid_boxes(self):
        model = Mock()
        model.predict.side_effect = [[], [Plate(Detection(Box(10, 10, 30, 30)))]]
        frame = np.zeros((50, 80, 3), dtype=np.uint8)
        result = predict_with_vehicle_crops(model, frame,
            [[200, 200, 250, 250], [30, 30, 10, 10], [0, float('nan'), 20, 20], [-20, -20, 60, 40]])
        self.assertEqual(len(result), 1)
        self.assertEqual(model.predict.call_count, 2)
        self.assertEqual(model.predict.call_args_list[1].args[0].shape, (40, 60, 3))

    def test_no_vehicle_preserves_whole_frame_detection(self):
        plate = Plate(Detection(Box(1, 2, 20, 10)))
        model = Mock()
        model.predict.return_value = [plate]
        self.assertEqual(predict_with_vehicle_crops(model, np.zeros((30, 40, 3)), []), [plate])
        model.predict.assert_called_once()


if __name__ == '__main__':
    unittest.main()
