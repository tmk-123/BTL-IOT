from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from line_selector import select_line
import cv2


class SelectorTests(unittest.TestCase):
    def test_live_updates_stop_after_first_click(self):
        frame = np.zeros((60, 100, 3), dtype=np.uint8)
        callback = []
        step = [0]
        read = Mock(return_value=(True, frame))
        def key(delay):
            step[0] += 1
            if step[0] == 1: callback[0](cv2.EVENT_LBUTTONDOWN, 100, 200, None, None)
            elif step[0] == 2: callback[0](cv2.EVENT_LBUTTONDOWN, 900, 200, None, None)
            return 13 if step[0] == 3 else -1
        with patch('line_selector.cv2.namedWindow'), patch('line_selector.cv2.resizeWindow'), patch('line_selector.cv2.imshow'), \
             patch('line_selector.cv2.destroyWindow') as close, \
             patch('line_selector.cv2.setMouseCallback', side_effect=lambda name, fn: callback.append(fn)), \
             patch('line_selector.cv2.getWindowProperty', return_value=1), patch('line_selector.cv2.waitKey', side_effect=key):
            line = select_line(frame, read_frame=read)
        self.assertEqual(read.call_count, 1)
        self.assertAlmostEqual(line[0], 100/999)
        self.assertAlmostEqual(line[1], 200/599)
        self.assertAlmostEqual(line[2], 900/999)
        close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
