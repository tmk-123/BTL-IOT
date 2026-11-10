from pathlib import Path
from contextlib import closing
from datetime import date
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
                if index == 3:
                    event.update(plate_text='30A33918', plate_status='consensus', plate_vote_share=.8)
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

    def test_search_by_plate_and_legacy_database(self):
        rows, total, _ = load_events(self.db, search='30a339')
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]['plate_text'], '30A33918')
        import sqlite3
        with closing(sqlite3.connect(self.db)) as connection:
            for name in ('plate_text', 'plate_status', 'plate_vote_share', 'plate_image'):
                connection.execute(f'ALTER TABLE events DROP COLUMN {name}')
            connection.commit()
        before = self.db.read_bytes()
        rows, total, _ = load_events(self.db)
        self.assertEqual(total, 3)
        self.assertIsNone(rows[0]['plate_text'])
        self.assertEqual(before, self.db.read_bytes())

    def test_streamlit_filters_and_missing_evidence(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "python/dashboard.py"), default_timeout=15).run()
        app.selectbox(key="dataset").select("Đường dẫn khác").run()
        app.text_input(key="database").input(str(self.db)).run()
        app.checkbox(key='show_journal').check().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1")
        self.assertEqual(len([b for b in app.button if b.key and b.key.startswith('details:')]), 3)
        app.text_input(key='search').input('30a339').run()
        self.assertEqual(app.metric[0].value, '0')
        self.assertIn('30A33918', app.button(key='details:test:3').label)
        app.text_input(key='search').input('').run()
        app.selectbox(key="journal_assessment").select("suspected_red_light").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1")
        # Evidence removed after capture: UI must show a warning instead of crashing.
        for image in (self.root / "evidence").glob("*/*.jpg"):
            image.unlink()
        app.button(key='details:test:1').click().run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(len(app.warning), 3)
        app.text_input(key="search").input("no-such-event").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")

    def test_suspected_view_dates_and_page_reset(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'python/dashboard.py'), default_timeout=15).run()
        app.selectbox(key='dataset').select('Đường dẫn khác').run()
        app.text_input(key='database').input(str(self.db)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '1')
        self.assertIn('Nghi vượt đèn đỏ', app.button(key='details:test:1').label)
        self.assertEqual(len(app.metric), 1)
        self.assertFalse(app.radio)
        self.assertFalse(app.number_input)
        self.assertEqual(app.text_input(key='search').label, 'Tìm biển số')
        self.assertFalse(any('Xe tải' in b.label or 'Ô tô' in b.label for b in app.button))
        app.checkbox(key='show_journal').check().run()
        app.text_input(key='search').input('30A33918').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['page'], 1)
        self.assertEqual(app.metric[0].value, '0')
        self.assertIn('30A33918', app.button(key='details:test:3').label)
        app.checkbox(key='by_date').check().run()
        app.date_input(key='date_from').set_value(date(2026, 11, 2))
        app.date_input(key='date_to').set_value(date(2026, 11, 2)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '0')
        app.date_input(key='date_from').set_value(date(2026, 11, 3)).run()
        self.assertEqual(len(app.error), 1)

    def test_yellow_and_red_share_suspected_total_and_keep_color_filters(self):
        store = EventStore(self.db, self.root / 'evidence')
        try:
            event = dict(event_id='test:yellow', session_id='test', frame=4, track_id=4,
                         observed_at='2026-11-02T10:01:00+07:00', vehicle_class='car', confidence=.9,
                         direction='negative_to_positive', light_state='YELLOW', assessment='suspected_yellow_light',
                         assessment_reason='continuous_yellow_during_crossing', source='test-source', bbox=[0, 0, 10, 10])
            frame = np.zeros((20, 20, 3), dtype=np.uint8)
            store.save(event, frame, frame)
        finally:
            store.close()
        suspected = ('suspected_red_light', 'suspected_yellow_light')
        rows, total, summary = load_events(self.db, assessment=suspected, limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(total, 2)
        self.assertEqual(summary, {'suspected_red_light': 1, 'suspected_yellow_light': 1})
        self.assertEqual(load_events(self.db, assessment=suspected, light_state='YELLOW')[1], 1)
        self.assertEqual(load_events(self.db, assessment=('suspected_red_light', "' OR 1=1 --"))[1], 1)
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'python/dashboard.py'), default_timeout=15).run()
        app.selectbox(key='dataset').select('Đường dẫn khác').run()
        app.text_input(key='database').input(str(self.db)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '2')
        self.assertEqual(app.metric[0].label, 'Tổng lượt nghi vượt đèn')
        self.assertIn('Nghi vượt đèn đỏ', app.button(key='details:test:1').label)
        self.assertIn('Nghi vượt đèn vàng', app.button(key='details:test:yellow').label)
        app.selectbox(key='violation_color').select('YELLOW').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '1')
        self.assertIn('Nghi vượt đèn vàng', app.button(key='details:test:yellow').label)
        app.checkbox(key='show_journal').check().run()
        app.selectbox(key='journal_assessment').select('suspected_yellow_light').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '1')
        app.button(key='details:test:yellow').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Nghi vượt đèn vàng' in warning.value for warning in app.warning))

    def test_plate_search_excludes_event_ids_and_legacy_metadata(self):
        self.assertEqual(load_events(self.db, search='test-source')[1], 3)
        self.assertEqual(load_events(self.db, search='test-source', plate_only=True)[1], 0)
        self.assertEqual(load_events(self.db, search='test:1', plate_only=True)[1], 0)
        self.assertEqual(load_events(self.db, search='30a339', plate_only=True)[1], 1)
        import sqlite3
        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute('ALTER TABLE events DROP COLUMN plate_text')
            connection.commit()
        self.assertEqual(load_events(self.db, search='test-source', plate_only=True)[1], 0)

    def test_footer_pagination_resets_after_search_and_page_size_changes(self):
        from streamlit.testing.v1 import AppTest
        store = EventStore(self.db, self.root / 'evidence')
        try:
            for index in range(27):
                event = dict(event_id=f'pages:{index}', session_id='pages', frame=index, track_id=index,
                             observed_at=f'2026-11-05T13:{index:02d}:00+07:00', vehicle_class='car', confidence=.9,
                             direction='negative_to_positive', light_state='RED', assessment='suspected_red_light',
                             assessment_reason='test', source='test', bbox=[0, 0, 10, 10], plate_text='29A99999')
                frame = np.zeros((20, 20, 3), dtype=np.uint8)
                store.save(event, frame, frame)
        finally:
            store.close()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'python/dashboard.py'), default_timeout=15).run()
        app.selectbox(key='dataset').select('Đường dẫn khác').run()
        app.text_input(key='database').input(str(self.db)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '28')
        app.number_input(key='page').set_value(2).run()
        self.assertFalse(app.exception)
        self.assertEqual(len([b for b in app.button if b.key and b.key.startswith('details:')]), 3)
        app.text_input(key='search').input('no-such-plate').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['page'], 1)
        self.assertFalse(app.number_input)
        app.text_input(key='search').input('').run()
        app.selectbox(key='page_size').select(50).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.number_input)
        self.assertEqual(len([b for b in app.button if b.key and b.key.startswith('details:')]), 28)

    def test_click_opens_matching_evidence_for_same_plate_without_json(self):
        from streamlit.testing.v1 import AppTest
        store = EventStore(self.db, self.root / 'evidence')
        try:
            for name, color, assessment, minute, pixel in [
                    ('a', 'RED', 'suspected_red_light', '10', 40),
                    ('b', 'YELLOW', 'suspected_yellow_light', '20', 180)]:
                event = dict(event_id=f'detail:{name}', session_id='detail', frame=1, track_id=1,
                             observed_at=f'2026-11-05T13:{minute}:00+07:00', vehicle_class='car', confidence=.9,
                             direction='negative_to_positive', light_state=color, assessment=assessment,
                             assessment_reason='test', source='test', bbox=[0, 0, 10, 10],
                             plate_text='29A22222', plate_status='consensus', plate_bbox=[1, 1, 5, 5])
                frame = np.full((20, 20, 3), pixel, dtype=np.uint8)
                store.save(event, frame, frame)
        finally:
            store.close()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'python/dashboard.py'), default_timeout=15).run()
        app.selectbox(key='dataset').select('Đường dẫn khác').run()
        app.text_input(key='database').input(str(self.db)).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get('image'))  # Evidence only appears after a click.
        self.assertFalse(any(item.key == 'event_id' for item in app.selectbox))
        app.button(key='details:detail:a').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('13:10:00' in item.value for item in app.markdown))
        self.assertTrue(any('Nghi vượt đèn đỏ' in item.value for item in app.warning))
        first_images = [image.value[0] for image in app.get('image')]
        self.assertEqual(len(first_images), 4)
        self.assertFalse(app.get('json'))
        self.assertFalse(any('Thông tin kỹ thuật' in item.label for item in app.expander))
        app.button(key='details:detail:b').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('13:20:00' in item.value for item in app.markdown))
        self.assertFalse(any('13:10:00' in item.value for item in app.markdown))
        self.assertTrue(any('Nghi vượt đèn vàng' in item.value for item in app.warning))
        second_images = [image.value[0] for image in app.get('image')]
        self.assertEqual(len(second_images), 4)
        self.assertNotEqual(first_images, second_images)
        app.text_input(key='search').input('no-such-event').run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get('image'))  # No stale evidence after filtering.

    def test_demo_is_isolated_labelled_and_idempotent(self):
        from dashboard_demo import create_demo
        import json
        output = self.root / 'demo'
        self.assertEqual(create_demo(output), 7)
        self.assertEqual(create_demo(output), 0)
        rows, total, summary = load_events(output/'traffic.db')
        self.assertEqual(total, 7)
        self.assertEqual(summary['suspected_red_light'], 3)
        self.assertEqual(summary['suspected_yellow_light'], 1)
        self.assertTrue(all(json.loads(row['payload_json'])['simulation'] for row in rows))
        self.assertTrue(all(Path(row['annotated_image']).is_file() for row in rows))


if __name__ == "__main__":
    unittest.main()
