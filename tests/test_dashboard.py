from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from dashboard_data import load_events
from event_store import EventStore


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = self.root / "traffic.db"
        store = EventStore(self.db, self.root / "evidence")
        try:
            for index, assessment, color, kind, day in [
                    (1, "suspected_red_light", "RED", "car", "01"),
                    (2, "unverified", "UNKNOWN", "bus", "02"),
                    (3, "unverified", "UNKNOWN", "car", "02")]:
                event = dict(event_id=f"test:{index}", session_id="test", frame=index, track_id=index,
                             observed_at=f"2026-11-{day}T10:00:00+07:00", vehicle_class=kind, confidence=0.8,
                             direction="negative_to_positive", light_state=color, assessment=assessment,
                             assessment_reason="test", source="test-source", bbox=[0, 0, 10, 10])
                frame = np.zeros((20, 20, 3), dtype=np.uint8)
                store.save(event, frame, frame)
        finally:
            store.close()

    def tearDown(self):
        self.temporary.cleanup()

    def test_readonly_no_database_creation(self):
        missing = self.root / "missing.db"
        with self.assertRaises(FileNotFoundError):
            load_events(missing)
        self.assertFalse(missing.exists())

    def test_pagination_statistics_cover_all_filtered_rows(self):
        rows, total, summary = load_events(self.db, limit=1, offset=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(total, 3)
        self.assertEqual(summary, {"suspected_red_light": 1, "unverified": 2})

    def test_combined_filters_and_local_dates(self):
        rows, total, _ = load_events(self.db, assessment="unverified", vehicle_class="car", light_state="UNKNOWN",
                                     date_from="2026-11-02", date_to="2026-11-02")
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["event_id"], "test:3")

    def test_search_is_literal_and_bound(self):
        for search in ["%", "_", "' OR 1=1 --"]:
            self.assertEqual(load_events(self.db, search=search)[1], 0)
        self.assertEqual(load_events(self.db, search="test:2")[1], 1)

    def test_query_does_not_change_database(self):
        before = self.db.read_bytes()
        load_events(self.db)
        self.assertEqual(self.db.read_bytes(), before)

    def test_streamlit_filters_and_missing_evidence(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "python/dashboard.py"), default_timeout=15).run()
        app.selectbox(key="dataset").select("Đường dẫn khác").run()
        app.text_input(key="database").input(str(self.db)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "3")
        app.selectbox(key="assessment").select("suspected_red_light").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1")
        # Evidence removed after capture: UI must show a warning instead of crashing.
        for image in (self.root / "evidence").glob("*/*.jpg"):
            image.unlink()
        app.run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(len(app.warning), 3)
        app.text_input(key="search").input("no-such-event").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")


if __name__ == "__main__":
    unittest.main()
