"""Deterministic red-light logic demo; no camera, model, broker or ESP32 needed."""

import argparse
import json
from pathlib import Path

from light_state import LightState, assess_crossing
from line_crossing import LineCrossing


def lamp(t, color, seq=1, age=1000):
    return (t, "lamp", dict(device="esp32-inter1", state=color, seq=seq, ms_in_state=age,
                              duration_ms=10000, uptime_ms=int(t * 1000), reason="heartbeat"))


def vehicle(t, y, track_id=1):
    return (t, "vehicle", (track_id, (50, y)))


SCENARIOS = [
    ("red_crossing", [lamp(10, "RED"), vehicle(10.6, 40), vehicle(10.8, 60)], ["suspected_red_light"]),
    ("green_crossing", [lamp(10, "GREEN"), vehicle(10.6, 40), vehicle(10.8, 60)], ["no_red_light_evidence"]),
    ("yellow_crossing", [lamp(10, "YELLOW"), vehicle(10.6, 40), vehicle(10.8, 60)], ["suspected_yellow_light"]),
    ("yellow_stopped_before_line", [lamp(10, "YELLOW"), vehicle(10.6, 40), vehicle(10.8, 44)], []),
    ("green_crossing_then_yellow", [lamp(10, "GREEN"), vehicle(10.6, 40), vehicle(10.8, 60),
                                    lamp(10.9, "YELLOW", seq=2, age=0), vehicle(11, 62)], ["no_red_light_evidence"]),
    ("yellow_changes_to_red_during_crossing", [lamp(10, "YELLOW"), vehicle(10.6, 40),
                                               lamp(10.7, "RED", seq=2, age=0), vehicle(10.8, 60)], ["unverified"]),
    ("yellow_reverse_crossing", [lamp(10, "YELLOW"), vehicle(10.6, 60), vehicle(10.8, 40)], ["suspected_yellow_light"]),
    ("yellow_missing_heartbeat", [lamp(10, "YELLOW"), vehicle(11.6, 40), vehicle(11.8, 60)], ["unverified"]),
    ("stopped_before_line", [lamp(10, "RED"), vehicle(10.6, 40), vehicle(10.8, 44), vehicle(11, 44)], []),
    ("already_past_line_when_red", [vehicle(9.9, 60), lamp(10, "RED"), vehicle(10.6, 62)], []),
    ("green_crossing_then_red", [lamp(10, "GREEN"), vehicle(10.6, 40), vehicle(10.8, 60),
                                 lamp(10.9, "RED", seq=2, age=0), vehicle(11, 62)], ["no_red_light_evidence"]),
    ("light_changes_during_crossing", [lamp(10, "GREEN"), vehicle(10.6, 40), lamp(10.7, "RED", seq=2, age=0),
                                      vehicle(10.8, 60)], ["unverified"]),
    ("missing_light", [vehicle(10.6, 40), vehicle(10.8, 60)], ["unverified"]),
    ("heartbeat_expired", [lamp(10, "RED"), vehicle(11.6, 40), vehicle(11.8, 60)], ["unverified"]),
    ("offline_during_crossing", [lamp(10, "RED"), vehicle(10.6, 40), (10.7, "offline", None),
                                  vehicle(10.8, 60)], ["unverified"]),
    ("red_reverse_crossing", [lamp(10, "RED"), vehicle(10.6, 60), vehicle(10.8, 40)], ["suspected_red_light"]),
    ("no_duplicate_after_crossing", [lamp(10, "RED"), vehicle(10.6, 40), vehicle(10.8, 60), vehicle(10.9, 61),
                                      vehicle(11, 62)], ["suspected_red_light"]),
    ("changed_id_not_inferred", [lamp(10, "RED"), vehicle(10.6, 40, 1), vehicle(10.8, 60, 2)], []),
    ("jitter_around_line", [lamp(10, "RED"), vehicle(10.6, 40), vehicle(10.7, 49), vehicle(10.8, 51),
                              vehicle(10.9, 48), vehicle(11, 40)], []),
]


def run_scenario(actions):
    light = LightState()
    line = LineCrossing((0, 50), (100, 50), margin=5)
    events = []
    frame = 0
    for t, kind, value in actions:
        if kind == "lamp":
            light.ingest(json.dumps(value), now=t)
        elif kind == "offline":
            light.unknown(now=t)
        else:
            frame += 1
            track_id, point = value
            line.expire(frame)
            direction = line.update(track_id, point, frame, t)
            if direction:
                decision = assess_crossing(light, *line.last_interval, direction=direction)
                events.append(dict(frame=frame, track_id=track_id, direction=direction, **decision))
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/demos/red_light_logic.json")
    args = parser.parse_args()
    report = []
    for name, actions, expected in SCENARIOS:
        events = run_scenario(actions)
        actual = [event["assessment"] for event in events]
        passed = actual == expected
        print(f"{'PASS' if passed else 'FAIL'} | {name}: {', '.join(actual) if actual else 'no crossing'}")
        report.append(dict(scenario=name, passed=passed, expected=expected, events=events))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(simulation=True, scenarios=report), indent=2), encoding="utf-8")
    print(f"SIMULATION ONLY. Report: {args.output}")
    return 0 if all(result["passed"] for result in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
