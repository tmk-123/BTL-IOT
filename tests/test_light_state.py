import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from light_state import LightState, classify_crossing
from line_crossing import LineCrossing


def message(state="RED", seq=3, age=1000, uptime=20000, reason="heartbeat"):
    return json.dumps(dict(device="esp32-inter1", state=state, seq=seq, ms_in_state=age,
                           duration_ms=10000, uptime_ms=uptime, reason=reason))


class LightTests(unittest.TestCase):
    def setUp(self):
        self.light = LightState()

    def test_no_messages(self):
        self.assertEqual(self.light.state_between(0, 1), "UNKNOWN")

    def test_red_green_yellow_classification(self):
        for color, expected in [("RED", "suspected_red_light"), ("GREEN", "no_red_light_evidence"),
                                ("YELLOW", "no_red_light_evidence")]:
            light = LightState()
            light.ingest(message(color), now=10)
            self.assertEqual(classify_crossing(light, 10.1, 10.5), (color, expected))

    def test_wrong_direction_not_flagged(self):
        self.light.ingest(message(), now=10)
        self.assertEqual(classify_crossing(self.light, 10.1, 10.5, False)[1], "not_applicable_direction")

    def test_expiry(self):
        self.light.ingest(message(), now=10)
        self.assertEqual(self.light.state_between(11.5, 11.5), "UNKNOWN")

    def test_no_backfill_before_first_message(self):
        self.light.ingest(message(), now=10)
        self.assertEqual(self.light.state_between(9.9, 10.5), "UNKNOWN")

    def test_continuous_heartbeat(self):
        self.light.ingest(message(), now=10)
        self.light.ingest(message(age=2000, uptime=21000), now=11)
        self.assertEqual(self.light.state_between(10.5, 12), "RED")

    def test_missing_heartbeat_leaves_gap(self):
        self.light.ingest(message(), now=10)
        self.light.ingest(message(age=4000, uptime=23000), now=13)
        self.assertEqual(self.light.state_between(10.5, 13.5), "UNKNOWN")

    def test_offline_disconnect_and_reconnect(self):
        self.light.ingest(message(), now=10)
        self.light.unknown(now=10.5)
        self.assertEqual(self.light.state_between(10.6, 10.7), "UNKNOWN")
        self.light.ingest(message(age=2000, uptime=21000), now=11)
        self.assertEqual(self.light.state_between(10.4, 11.2), "UNKNOWN")
        self.assertEqual(self.light.state_between(11.1, 11.2), "RED")

    def test_transition_inside_crossing_window(self):
        self.light.ingest(message("GREEN"), now=10)
        self.light.ingest(message("RED", seq=4, age=0, uptime=21000), now=11)
        self.assertEqual(self.light.state_between(10.5, 11.2), "UNKNOWN")

    def test_estimated_transition_cuts_old_color_early(self):
        self.light.ingest(message(), now=10)
        self.light.ingest(message("GREEN", seq=4, age=400, uptime=21000), now=11)
        self.assertEqual(self.light.state_between(10.7, 10.8), "UNKNOWN")

    def test_duration_expiry(self):
        self.light.ingest(message(age=9900), now=10)
        self.assertEqual(self.light.state_between(10.2, 10.2), "UNKNOWN")

    def test_malformed_and_retained_invalidate(self):
        for payload, retained in [("test", False), ("[]", False), (message(), True),
                                  (message(age=10000), False), (message("BLUE"), False)]:
            light = LightState()
            light.ingest(message(), now=10)
            self.assertFalse(light.ingest(payload, retained=retained, now=10.2))
            self.assertEqual(light.state_between(10.3, 10.4), "UNKNOWN")

    def test_device_filter(self):
        self.assertFalse(self.light.ingest(message().replace("esp32-inter1", "other"), now=10))
        self.assertEqual(self.light.state_between(10, 10), "UNKNOWN")

    def test_sequence_and_uptime_backwards(self):
        for payload in [message(seq=2, uptime=21000), message(uptime=100)]:
            light = LightState()
            light.ingest(message(), now=10)
            self.assertFalse(light.ingest(payload, now=11))
            self.assertEqual(light.state_between(11.1, 11.2), "UNKNOWN")

    def test_reboot_breaks_continuity(self):
        self.light.ingest(message(), now=10)
        self.light.ingest(message(seq=1, age=0, uptime=100, reason="connect"), now=11)
        self.assertEqual(self.light.state_between(10.5, 11.2), "UNKNOWN")

    def test_crossing_uses_previous_stable_point_time(self):
        line = LineCrossing((0, 50), (100, 50))
        line.update(1, (50, 40), 1, 10.1)
        line.update(1, (50, 50), 2, 10.4)
        self.assertEqual(line.update(1, (50, 60), 3, 10.7), "negative_to_positive")
        self.assertEqual(line.last_interval, (10.1, 10.7))
        self.light.ingest(message(), now=10)
        self.assertEqual(classify_crossing(self.light, *line.last_interval)[1], "suspected_red_light")


if __name__ == "__main__":
    unittest.main()
