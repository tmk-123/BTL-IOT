"""Store crossing metadata in SQLite and JPEG evidence as separate files."""

import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import tempfile

import cv2


class EventStore:
    def __init__(self, database, evidence_dir):
        self.database = Path(database).resolve()
        self.evidence_dir = Path(evidence_dir).resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                frame INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                observed_at TEXT NOT NULL,
                vehicle_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                direction TEXT NOT NULL,
                light_state TEXT NOT NULL,
                assessment TEXT NOT NULL,
                assessment_reason TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_image TEXT,
                annotated_image TEXT,
                vehicle_image TEXT,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_time ON events(observed_at);
            CREATE INDEX IF NOT EXISTS events_assessment ON events(assessment);
        """)
        # Additive migration: keep existing events/images and support older databases.
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            columns = {row[1] for row in self.connection.execute('PRAGMA table_info(events)')}
            for name, kind in {'plate_text': 'TEXT', 'plate_status': "TEXT DEFAULT 'not_enabled'",
                               'plate_vote_share': 'REAL', 'plate_image': 'TEXT'}.items():
                if name not in columns:
                    self.connection.execute(f'ALTER TABLE events ADD COLUMN {name} {kind}')
            self.connection.execute('COMMIT')
        except BaseException:
            self.connection.execute('ROLLBACK')
            raise

    def close(self):
        self.connection.close()

    @staticmethod
    def write_jpeg(path, frame):
        if frame is None or frame.size == 0:
            raise ValueError("Evidence frame is empty")
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise OSError("Cannot encode evidence JPEG")
        # Exclusive creation: never overwrite evidence belonging to another event.
        with path.open("xb") as output:
            output.write(encoded.tobytes())

    def save(self, event, frame=None, annotated=None, save_all=False):
        """Return persisted event and inserted flag. Duplicate IDs do not write files."""
        stage = None
        finalized = None
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute("SELECT payload_json FROM events WHERE event_id=?",
                                               (event["event_id"],)).fetchone()
            if existing:
                self.connection.execute("COMMIT")
                return json.loads(existing["payload_json"]), False
            saved = dict(event)
            saved.update(raw_image=None, annotated_image=None, vehicle_image=None, plate_image=None)
            saved.setdefault('plate_text', None)
            saved.setdefault('plate_status', 'not_enabled')
            saved.setdefault('plate_vote_share', None)
            if save_all or event["assessment"] == "suspected_red_light":
                if frame is None or annotated is None:
                    raise ValueError("Evidence requires original and annotated frames")
                height, width = frame.shape[:2]
                bbox = event.get("bbox")
                if bbox is None or len(bbox) != 4 or not all(math.isfinite(v) for v in bbox):
                    raise ValueError("Evidence requires a finite bbox")
                x1, y1 = max(0, math.floor(bbox[0])), max(0, math.floor(bbox[1]))
                x2, y2 = min(width, math.ceil(bbox[2])), min(height, math.ceil(bbox[3]))
                if x1 >= x2 or y1 >= y2:
                    raise ValueError("Vehicle crop lies outside the image")
                self.evidence_dir.mkdir(parents=True, exist_ok=True)
                folder = self.evidence_dir / hashlib.sha256(event["event_id"].encode()).hexdigest()
                if folder.exists():
                    raise OSError(f"Evidence directory already exists without a database row: {folder}")
                stage = Path(tempfile.mkdtemp(prefix=".pending-", dir=self.evidence_dir))
                self.write_jpeg(stage / "original.jpg", frame)
                self.write_jpeg(stage / "annotated.jpg", annotated)
                self.write_jpeg(stage / "vehicle.jpg", frame[y1:y2, x1:x2])
                plate_box = event.get('plate_bbox')
                if plate_box is not None:
                    if len(plate_box) != 4 or not all(math.isfinite(value) for value in plate_box):
                        raise ValueError('Plate crop requires a finite bbox')
                    px1, py1 = max(0, math.floor(plate_box[0])), max(0, math.floor(plate_box[1]))
                    px2, py2 = min(width, math.ceil(plate_box[2])), min(height, math.ceil(plate_box[3]))
                    if px1 >= px2 or py1 >= py2:
                        raise ValueError('Plate crop lies outside the image')
                    self.write_jpeg(stage / 'plate.jpg', frame[py1:py2, px1:px2])
                stage.rename(folder)
                stage = None
                finalized = folder
                saved.update(raw_image=str(folder / "original.jpg"),
                             annotated_image=str(folder / "annotated.jpg"),
                             vehicle_image=str(folder / "vehicle.jpg"))
                if plate_box is not None:
                    saved['plate_image'] = str(folder / 'plate.jpg')
            columns = ("event_id", "session_id", "frame", "track_id", "observed_at", "vehicle_class",
                       "confidence", "direction", "light_state", "assessment", "assessment_reason", "source",
                       "raw_image", "annotated_image", "vehicle_image", "plate_text", "plate_status",
                       "plate_vote_share", "plate_image")
            values = [saved[key] for key in columns]
            self.connection.execute(
                f"INSERT INTO events ({','.join(columns)},payload_json) VALUES ({','.join('?' for _ in range(len(columns)+1))})",
                values + [json.dumps(saved, ensure_ascii=False, allow_nan=False)])
            self.connection.execute("COMMIT")
            return saved, True
        except BaseException:
            if self.connection.in_transaction:
                self.connection.execute("ROLLBACK")
            # Only remove directories created by this call, never pre-existing evidence.
            for created in (stage, finalized):
                if created is not None:
                    shutil.rmtree(created)
            raise
