"""Save one explicitly simulated red-light event and its JPEGs; no hardware required."""

import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from event_store import EventStore
from red_light_demo import SCENARIOS, run_scenario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/demos/storage")
    args = parser.parse_args()
    frame = np.full((360, 640, 3), 210, dtype=np.uint8)
    cv2.line(frame, (30, 240), (610, 240), (255, 255, 255), 5)
    cv2.rectangle(frame, (240, 190), (400, 290), (170, 70, 20), -1)
    cv2.putText(frame, "SIMULATION - not a real violation", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    annotated = frame.copy()
    cv2.rectangle(annotated, (240, 190), (400, 290), (0, 0, 255), 3)
    cv2.putText(annotated, "ID 1 | RED | suspected_red_light", (10, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    decision = run_scenario(SCENARIOS[0][1])[0]
    session = "demo-" + uuid4().hex
    event = dict(decision, event_id=f"{session}:2:1", session_id=session,
                 observed_at=datetime.now().astimezone().isoformat(), source="simulation:drawn_vehicle",
                 vehicle_class="car", confidence=1.0, bbox=[240, 190, 400, 290], simulation=True)
    store = EventStore(args.output / "traffic.db", args.output / "evidence")
    try:
        saved, inserted = store.save(event, frame, annotated)
        _, duplicate = store.save(event, frame, annotated)
        if not inserted or duplicate:
            raise RuntimeError("Idempotency check failed")
        print("SIMULATION: saved one event; duplicate submission ignored.")
        print(f"Database: {store.database}")
        for key in ("raw_image", "annotated_image", "vehicle_image"):
            print(f"{key}: {saved[key]}")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
