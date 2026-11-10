"""Overlap HTTP snapshots with inference, retaining only the newest observation."""

from datetime import datetime
import threading
import time

from camera_viewer import SnapshotCapture


class LatestSnapshotCapture:
    def __init__(self, url, capture=None):
        self.capture = capture if capture is not None else SnapshotCapture(url)
        self.condition = threading.Condition()
        self.stop = threading.Event()
        self.latest = None
        self.gap = False
        self.terminal = False
        self.discontinuity = False
        self.observed_mono = None
        self.observed_at = None
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _run(self):
        failures = 0
        try:
            while not self.stop.is_set():
                ok, frame = self.capture.read()
                timestamp = time.monotonic()
                observed_at = datetime.now().astimezone().isoformat()
                with self.condition:
                    if self.stop.is_set():
                        break
                    # A later successful frame must not hide a camera outage.
                    self.gap |= not ok
                    self.latest = (ok, frame, timestamp, observed_at)
                    failures = 0 if ok else failures + 1
                    self.terminal = failures >= 3
                    self.condition.notify_all()
                if self.terminal or (not ok and self.stop.wait(.3)):
                    break
        finally:
            with self.condition:
                self.terminal = True
                self.condition.notify_all()

    def read(self):
        with self.condition:
            available = self.condition.wait_for(
                lambda: self.latest is not None or self.terminal or self.stop.is_set(), timeout=6)
            if not available or self.latest is None:
                self.discontinuity = True
                return False, None
            ok, frame, self.observed_mono, self.observed_at = self.latest
            self.latest = None  # Never process/vote on the same delivered frame twice.
            self.discontinuity = self.gap
            self.gap = False
            return ok, frame

    def release(self):
        self.stop.set()
        with self.condition:
            self.condition.notify_all()
        self.capture.release()
        self.worker.join(timeout=6)
