"""Create clearly simulated dashboard examples, isolated from real traffic events."""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np

from event_store import EventStore

ROOT = Path(__file__).resolve().parents[1]


def create_demo(output):
    store = EventStore(output/'traffic.db', output/'evidence')
    inserted = 0
    today = datetime.now(ZoneInfo('Asia/Bangkok')).replace(hour=9, minute=0, second=0, microsecond=0)
    scenarios = [('suspected_red_light', 'RED', 'car', '29A33185'),
                 ('suspected_red_light', 'RED', 'motorcycle', '59U116124'),
                 ('suspected_red_light', 'RED', 'truck', None),
                 ('unverified', 'UNKNOWN', 'car', '30A61235'),
                 ('no_red_light_evidence', 'GREEN', 'car', '30F21717'),
                 ('unverified', 'UNKNOWN', 'bus', None),
                 ('suspected_yellow_light', 'YELLOW', 'car', '30A33918')]
    try:
        for index, (assessment, color, kind, plate) in enumerate(scenarios):
            frame = np.full((540, 960, 3), (55, 65, 75), dtype=np.uint8)
            cv2.rectangle(frame, (0, 0), (959, 100), (235, 240, 245), -1)
            cv2.putText(frame, 'DEMO / SIMULATED EVENT', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 35, 50), 2)
            for x in (160, 480, 800): cv2.line(frame, (x, 140), (x, 530), (100, 110, 120), 4)
            cv2.line(frame, (60, 365), (900, 365), (230, 230, 230), 10)
            cv2.rectangle(frame, (325, 200), (635, 440), (150, 115, 70), -1)
            cv2.rectangle(frame, (350, 215), (610, 305), (65, 60, 45), -1)
            cv2.rectangle(frame, (353, 355), (610, 402), (245, 245, 245), -1)
            cv2.putText(frame, plate or 'UNREADABLE', (362, 389), cv2.FONT_HERSHEY_SIMPLEX, .7, (20, 20, 20), 2)
            tint = {'RED': (60, 60, 230), 'YELLOW': (0, 210, 255), 'GREEN': (70, 190, 70)}.get(color, (130, 130, 130))
            cv2.circle(frame, (870, 175), 24, tint, -1)
            cv2.putText(frame, f'{kind.upper()} | {color}', (30, 500), cv2.FONT_HERSHEY_SIMPLEX, .75, (245, 245, 245), 2)
            annotated = frame.copy()
            cv2.rectangle(annotated, (325, 200), (635, 440), (0, 210, 255), 3)
            cv2.rectangle(annotated, (353, 355), (610, 402), (70, 230, 70), 2)
            timestamp = today + timedelta(minutes=7*index, days=-1 if index in (1, 5) else 0)
            event = dict(event_id=f'dashboard-demo-v1:{index+1}', session_id='dashboard-demo-v1',
                         frame=index+1, track_id=index+1, observed_at=timestamp.isoformat(),
                         vehicle_class=kind, confidence=.9, direction='negative_to_positive',
                         light_state=color, assessment=assessment, assessment_reason='simulated_dashboard_scenario',
                         source='simulation:dashboard_demo', bbox=[325, 200, 635, 440],
                         plate_bbox=[353, 355, 610, 402] if plate else None,
                         plate_text=plate, plate_status='consensus' if plate else 'pending',
                         plate_vote_share=.9 if plate else None, simulation=True,
                         event_type='line_crossing')
            _, new = store.save(event, frame, annotated, save_all=True)
            inserted += new
    finally:
        store.close()
    return inserted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/demos/dashboard')
    args = parser.parse_args()
    count = create_demo(args.output)
    print(f'DEMO: {count} new event(s). Database: {(args.output/"traffic.db").resolve()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
