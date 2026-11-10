from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from light_state import LightState, assess_crossing
from red_light_demo import SCENARIOS, lamp, run_scenario
import json


class RedLightTests(unittest.TestCase):
    def test_vehicle_and_light_scenarios(self):
        for name, actions, expected in SCENARIOS:
            with self.subTest(scenario=name):
                self.assertEqual([event["assessment"] for event in run_scenario(actions)], expected)

    def test_guard_near_red_onset(self):
        light = LightState()
        light.ingest(json.dumps(lamp(10, "RED")[2]), now=10)
        result = assess_crossing(light, 10.2, 10.4, "negative_to_positive")
        self.assertEqual(result["assessment"], "unverified")

    def test_yellow_requires_stable_color_and_preserves_actual_light(self):
        light = LightState()
        light.ingest(json.dumps(lamp(10, "YELLOW")[2]), now=10)
        result = assess_crossing(light, 10.6, 10.8, "negative_to_positive")
        self.assertEqual(result, dict(light_state="YELLOW", assessment="suspected_yellow_light",
                                     assessment_reason="continuous_yellow_during_crossing"))
        self.assertEqual(assess_crossing(light, 10.2, 10.4, "negative_to_positive")["assessment"], "unverified")

    def test_no_source_reason(self):
        self.assertEqual(assess_crossing(None, 10, 11, "negative_to_positive")["assessment_reason"], "no_light_source")

    def test_invalid_times_cannot_produce_red(self):
        light = LightState()
        light.ingest(json.dumps(lamp(10, "RED")[2]), now=10)
        for start, end in [(float("nan"), 11), (10, float("inf")), (11, 10)]:
            with self.subTest(start=start, end=end):
                self.assertEqual(light.state_between(start, end), "UNKNOWN")
                self.assertEqual(assess_crossing(light, start, end, "negative_to_positive")["assessment"], "unverified")

    def test_configured_reverse_direction(self):
        light = LightState()
        light.ingest(json.dumps(lamp(10, "RED")[2]), now=10)
        self.assertEqual(assess_crossing(light, 10.6, 10.8, "positive_to_negative",
                                       expected_direction="positive_to_negative")["assessment"], "suspected_red_light")

    def test_demo_default_checks_both_directions_using_the_same_light_rules(self):
        for color, expected in [('RED', 'suspected_red_light'), ('YELLOW', 'suspected_yellow_light'),
                                ('GREEN', 'no_red_light_evidence')]:
            light = LightState()
            light.ingest(json.dumps(lamp(10, color)[2]), now=10)
            for direction in ('negative_to_positive', 'positive_to_negative'):
                with self.subTest(color=color, direction=direction):
                    result = assess_crossing(light, 10.6, 10.8, direction)
                    self.assertEqual(result['assessment'], expected)
                    self.assertEqual(result['light_state'], color)
                    self.assertEqual(assess_crossing(light, 10.2, 10.4, direction)['assessment'], 'unverified')
        self.assertEqual(assess_crossing(None, 10, 11, 'positive_to_negative')['assessment'], 'unverified')


if __name__ == "__main__":
    unittest.main()
