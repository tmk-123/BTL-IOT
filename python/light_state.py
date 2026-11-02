"""Validate MQTT lamp messages and query conservative receive-time intervals."""

from collections import deque
from dataclasses import dataclass
import json
from math import isfinite
from threading import RLock
import time


@dataclass
class Sample:
    received: float
    expires: float
    state: str
    seq: int | None = None
    uptime: int | None = None


class LightState:
    def __init__(self, stale_after=1.5, device="esp32-inter1"):
        if not isfinite(stale_after) or stale_after <= 0:
            raise ValueError("stale_after must be finite and positive")
        self.stale_after, self.device = stale_after, device
        self.samples = deque(maxlen=1000)
        self.lock = RLock()

    def unknown(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            self.samples.append(Sample(now, now, "UNKNOWN"))

    def ingest(self, payload, retained=False, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            try:
                value = json.loads(payload)
                if not isinstance(value, dict):
                    raise ValueError("Expected JSON object")
                if value.get("device") != self.device:
                    return False
                if retained or value.get("state") not in {"RED", "YELLOW", "GREEN"}:
                    raise ValueError("Retained or unsupported state")
                for key in ("seq", "ms_in_state", "duration_ms", "uptime_ms"):
                    if type(value.get(key)) is not int or not 0 <= value[key] <= 0xFFFFFFFF:
                        raise ValueError("Invalid numeric field")
                age, duration, uptime, seq = (value[k] for k in ("ms_in_state", "duration_ms", "uptime_ms", "seq"))
                if not 0 <= age < duration or age > uptime:
                    raise ValueError("Invalid lamp timing")
                if value.get("reason") not in {"connect", "change", "heartbeat"}:
                    raise ValueError("Invalid reason")
                previous = self.samples[-1] if self.samples else None
                if previous and previous.uptime is not None:
                    if uptime < previous.uptime:
                        if value["reason"] != "connect":
                            raise ValueError("Uptime went backwards without reconnect")
                        # Reboot or reordered packet: break continuity, never bridge it.
                        self.unknown(now)
                    elif seq < previous.seq or (seq == previous.seq and value["state"] != previous.state):
                        raise ValueError("Out-of-order or contradictory state")
                    elif seq != previous.seq:
                        # End old knowledge at estimated transition, not delayed receipt.
                        previous.expires = min(previous.expires, max(previous.received, now - age / 1000))
                self.samples.append(Sample(now, min(now + self.stale_after, now + (duration - age) / 1000),
                                           value["state"], seq, uptime))
                return True
            except (ValueError, TypeError, UnicodeError):
                self.unknown(now)
                return False

    def state_between(self, start, end):
        """Require uninterrupted, fresh knowledge of one color across [start, end]."""
        if not isfinite(start) or not isfinite(end) or start > end:
            return "UNKNOWN"
        with self.lock:
            samples = list(self.samples)
            if any(sample.state == "UNKNOWN" and start < sample.received <= end for sample in samples):
                return "UNKNOWN"
            covered, color, sequence = start, None, None
            for i, sample in enumerate(samples):
                until = min(sample.expires, samples[i + 1].received) if i + 1 < len(samples) else sample.expires
                if until < start or sample.received > end:
                    continue
                if sample.state == "UNKNOWN" or sample.received > covered or until < covered:
                    if sample.received <= covered < (samples[i + 1].received if i + 1 < len(samples) else float("inf")):
                        return "UNKNOWN"
                    continue
                if color is not None and (color != sample.state or sequence != sample.seq):
                    return "UNKNOWN"
                color = sample.state
                sequence = sample.seq
                covered = max(covered, until)
                if covered > end:  # Expiry itself is already unknown.
                    return color
            return "UNKNOWN"

    def current(self):
        now = time.monotonic()
        return self.state_between(now, now)


def classify_crossing(light, start, end, allowed_direction=True):
    state = light.state_between(start, end) if light else "UNKNOWN"
    if not allowed_direction:
        return state, "not_applicable_direction"
    if state == "RED":
        return state, "suspected_red_light"
    if state in {"GREEN", "YELLOW"}:
        return state, "no_red_light_evidence"
    return state, "unverified"


def assess_crossing(light, start, end, direction, expected_direction="negative_to_positive", timing_margin=0.5):
    """Explain a crossing decision; all times use the same monotonic clock."""
    directions = {"negative_to_positive", "positive_to_negative"}
    if direction not in directions or expected_direction not in directions:
        raise ValueError("Unsupported crossing direction")
    if not isfinite(timing_margin) or timing_margin < 0:
        raise ValueError("timing_margin must be finite and nonnegative")
    if not isfinite(start) or not isfinite(end) or start > end:
        return dict(light_state="UNKNOWN", assessment="unverified", assessment_reason="invalid_time_window")
    state, assessment = classify_crossing(light, start - timing_margin, end, direction == expected_direction)
    reasons = {
        "not_applicable_direction": "opposite_direction",
        "suspected_red_light": "continuous_red_during_crossing",
        "no_red_light_evidence": "continuous_green_or_yellow_during_crossing",
        "unverified": "missing_stale_or_changing_light" if light is not None else "no_light_source",
    }
    return dict(light_state=state, assessment=assessment, assessment_reason=reasons[assessment])
