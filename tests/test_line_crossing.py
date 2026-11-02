import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from line_crossing import LineCrossing


class CrossingTests(unittest.TestCase):
    def setUp(self):
        self.line = LineCrossing((10, 50), (90, 50), margin=3, max_gap=3)

    def sequence(self, points, track_id=1):
        return [self.line.update(track_id, point, i + 1) for i, point in enumerate(points)]

    def test_stopped_vehicle_does_not_cross(self):
        self.assertEqual(self.sequence([(50, 40)] * 20), [None] * 20)

    def test_one_event_after_deadband_then_no_duplicates(self):
        events = self.sequence([(50, 40), (50, 49), (50, 51), (50, 60), (50, 61)])
        self.assertEqual(events, [None, None, None, "negative_to_positive", None])

    def test_line_jitter_does_not_cross(self):
        self.assertTrue(all(event is None for event in self.sequence([(50, 40), (50, 49), (50, 51)] * 5)))

    def test_reverse_and_second_pass(self):
        self.assertEqual(self.sequence([(50, 40), (50, 60), (50, 40)]),
                         [None, "negative_to_positive", "positive_to_negative"])

    def test_outside_segment_is_not_crossing(self):
        self.assertEqual(self.sequence([(100, 40), (100, 60)]), [None, None])

    def test_long_missing_gap_does_not_invent_crossing(self):
        self.line.update(1, (50, 40), 1)
        self.assertIsNone(self.line.update(1, (50, 60), 5))

    def test_short_missing_gap_keeps_continuity(self):
        self.line.update(1, (50, 40), 1)
        self.assertEqual(self.line.update(1, (50, 60), 3), "negative_to_positive")

    def test_new_id_does_not_inherit_another_vehicle(self):
        self.line.update(1, (50, 40), 1)
        self.assertIsNone(self.line.update(2, (50, 60), 2))

    def test_vertical_and_diagonal_lines(self):
        for start, end in [((50, 10), (50, 90)), ((10, 10), (90, 90))]:
            line = LineCrossing(start, end, margin=2)
            self.assertIsNone(line.update(1, (70, 40), 1))
            self.assertEqual(line.update(1, (30, 60), 2), "negative_to_positive")

    def test_expire_removes_stale_state(self):
        self.line.update(1, (50, 40), 1)
        self.line.expire(5)
        self.assertFalse(self.line.states)

    def test_start_in_deadband_needs_a_previous_stable_side(self):
        self.assertEqual(self.sequence([(50, 50), (50, 60)]), [None, None])


if __name__ == "__main__":
    unittest.main()
