import json
from pathlib import Path
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from event_store import EventStore


def example_event(assessment="suspected_red_light"):
    return dict(event_id="session:3:1", session_id="session", frame=3, track_id=1,
                observed_at="2026-11-02T10:00:00+07:00", vehicle_class="car", confidence=0.9,
                direction="negative_to_positive", light_state="RED", assessment=assessment,
                assessment_reason="test", source="simulation", bbox=[10, 20, 80, 70])


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name) / "ảnh kiểm thử"
        self.db, self.images = root / "traffic.db", root / "evidence"
        self.store = EventStore(self.db, self.images)
        self.frame = np.full((100, 120, 3), 80, dtype=np.uint8)
        self.annotated = self.frame.copy()
        cv2.rectangle(self.annotated, (10, 20), (80, 70), (0, 0, 255), 3)

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def rows(self):
        return self.store.connection.execute("SELECT * FROM events").fetchall()

    def test_images_and_persistence(self):
        saved, inserted = self.store.save(example_event(), self.frame, self.annotated)
        self.assertTrue(inserted)
        for key in ("raw_image", "annotated_image", "vehicle_image"):
            self.assertTrue(Path(saved[key]).is_file())
        raw = cv2.imdecode(np.fromfile(saved["raw_image"], dtype=np.uint8), cv2.IMREAD_COLOR)
        crop = cv2.imdecode(np.fromfile(saved["vehicle_image"], dtype=np.uint8), cv2.IMREAD_COLOR)
        np.testing.assert_array_equal(raw, self.frame)
        self.assertEqual(crop.shape[:2], (50, 70))
        other = EventStore(self.db, self.images)
        try:
            payload = json.loads(other.connection.execute("SELECT payload_json FROM events").fetchone()[0])
            self.assertEqual(payload, saved)
        finally:
            other.close()

    def test_duplicate_id_does_not_write_again(self):
        saved, _ = self.store.save(example_event(), self.frame, self.annotated)
        duplicate, inserted = self.store.save(example_event(), None, None)
        self.assertFalse(inserted)
        self.assertEqual(duplicate, saved)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(len(list(self.images.glob("*/*.jpg"))), 3)

    def test_nonred_metadata_only(self):
        saved, _ = self.store.save(example_event("unverified"))
        self.assertIsNone(saved["raw_image"])
        self.assertFalse(self.images.exists())
        self.assertEqual(len(self.rows()), 1)

    def test_yellow_suspicion_saves_evidence_without_save_all(self):
        event = example_event("suspected_yellow_light")
        event.update(light_state="YELLOW", assessment_reason="continuous_yellow_during_crossing")
        saved, inserted = self.store.save(event, self.frame, self.annotated)
        self.assertTrue(inserted)
        self.assertEqual(saved['light_state'], 'YELLOW')
        for key in ('raw_image', 'annotated_image', 'vehicle_image'):
            self.assertTrue(Path(saved[key]).is_file())
        self.assertEqual(self.rows()[0]['assessment'], 'suspected_yellow_light')

    def test_save_all_keeps_unknown_assessment(self):
        saved, _ = self.store.save(example_event("unverified"), self.frame, self.annotated, save_all=True)
        self.assertEqual(saved["assessment"], "unverified")
        self.assertTrue(Path(saved["vehicle_image"]).exists())

    def test_crop_is_clipped_to_frame(self):
        event = example_event()
        event["bbox"] = [-10, -20, 130, 150]
        saved, _ = self.store.save(event, self.frame, self.annotated)
        crop = cv2.imdecode(np.fromfile(saved["vehicle_image"], dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(crop.shape, self.frame.shape)

    def test_invalid_crop_leaves_no_record_or_images(self):
        event = example_event()
        event["bbox"] = [130, 0, 150, 20]
        with self.assertRaises(ValueError):
            self.store.save(event, self.frame, self.annotated)
        self.assertEqual(len(self.rows()), 0)
        self.assertFalse(self.images.exists())

    def test_failed_image_write_rolls_back_and_cleans_partial_files(self):
        actual = self.store.write_jpeg
        def write(path, frame):
            if path.name == "vehicle.jpg":
                raise OSError("Simulated disk full")
            actual(path, frame)
        with patch.object(self.store, "write_jpeg", side_effect=write):
            with self.assertRaises(OSError):
                self.store.save(example_event(), self.frame, self.annotated)
        self.assertEqual(len(self.rows()), 0)
        self.assertEqual(list(self.images.iterdir()), [])
        # The same store can retry after the failure.
        self.assertTrue(self.store.save(example_event(), self.frame, self.annotated)[1])

    def test_insert_failure_cleans_finalized_images(self):
        event = example_event()
        event["session_id"] = None
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.save(event, self.frame, self.annotated)
        self.assertEqual(len(self.rows()), 0)
        self.assertEqual(list(self.images.iterdir()), [])

    def test_event_id_cannot_escape_evidence_folder(self):
        event = example_event()
        event["event_id"] = "../../outside:'; DROP TABLE events;--"
        saved, _ = self.store.save(event, self.frame, self.annotated)
        self.assertTrue(Path(saved["raw_image"]).is_relative_to(self.images))
        self.assertEqual(len(self.rows()), 1)

    def test_plate_metadata_crop_and_duplicate(self):
        event = example_event()
        event.update(plate_text='30A33918', plate_status='consensus', plate_vote_share=.8,
                     plate_bbox=[20, 40, 60, 55], plate_ocr=[{'raw_text': '30A33913'}])
        saved, inserted = self.store.save(event, self.frame, self.annotated)
        self.assertTrue(inserted)
        crop = cv2.imdecode(np.fromfile(saved['plate_image'], dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(crop.shape[:2], (15, 40))
        self.assertEqual(self.rows()[0]['plate_text'], '30A33918')
        self.assertEqual(json.loads(self.rows()[0]['payload_json'])['plate_ocr'], event['plate_ocr'])
        self.assertFalse(self.store.save(event)[1])
        self.assertEqual(len(list(self.images.glob('*/*.jpg'))), 4)

    def test_invalid_plate_crop_rolls_back_all_images(self):
        event = example_event()
        event['plate_bbox'] = [500, 500, 550, 520]
        with self.assertRaises(ValueError):
            self.store.save(event, self.frame, self.annotated)
        self.assertEqual(len(self.rows()), 0)
        self.assertEqual(list(self.images.iterdir()), [])

    def test_additive_migration_keeps_old_events(self):
        self.store.save(example_event('unverified'))
        for name in ('plate_text', 'plate_status', 'plate_vote_share', 'plate_image'):
            self.store.connection.execute(f'ALTER TABLE events DROP COLUMN {name}')
        self.store.close()
        self.store = EventStore(self.db, self.images)
        self.assertEqual(len(self.rows()), 1)
        self.assertIsNone(self.rows()[0]['plate_text'])
        self.assertEqual(self.rows()[0]['plate_status'], 'not_enabled')


if __name__ == "__main__":
    unittest.main()
