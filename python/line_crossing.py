"""Finite stop-line crossing with a pixel deadband and stale-track protection."""

from dataclasses import dataclass
from math import hypot


@dataclass
class TrackState:
    side: int
    point: tuple[float, float]
    last_seen: int
    observed_at: float


class LineCrossing:
    def __init__(self, start, end, margin=5.0, max_gap=5):
        self.start, self.end = start, end
        self.dx, self.dy = end[0] - start[0], end[1] - start[1]
        self.length = hypot(self.dx, self.dy)
        if self.length == 0 or margin < 0 or max_gap < 1:
            raise ValueError("Line endpoints must differ, margin >= 0 and max_gap >= 1")
        self.margin, self.max_gap = margin, max_gap
        self.states = {}
        self.last_interval = None

    def distance(self, point):
        return (self.dx * (point[1] - self.start[1]) - self.dy * (point[0] - self.start[0])) / self.length

    def expire(self, frame_index):
        self.states = {key: value for key, value in self.states.items()
                       if frame_index - value.last_seen <= self.max_gap}

    def update(self, track_id, point, frame_index, observed_at=None):
        """Return direction only on a stable side change across the finite segment.

        Positive side is below a left-to-right horizontal line in image coordinates.
        A point inside the deadband preserves the previous stable side.
        """
        observed_at = frame_index if observed_at is None else observed_at
        self.last_interval = None
        distance = self.distance(point)
        side = 1 if distance > self.margin else -1 if distance < -self.margin else 0
        previous = self.states.get(track_id)
        if previous is not None and frame_index - previous.last_seen > self.max_gap:
            previous = None
            self.states.pop(track_id, None)
        if side == 0:
            if previous is not None:
                previous.last_seen = frame_index
            return None
        self.states[track_id] = TrackState(side, point, frame_index, observed_at)
        if previous is None or previous.side == side:
            return None
        old_distance = self.distance(previous.point)
        fraction = old_distance / (old_distance - distance)
        cross = (previous.point[0] + fraction * (point[0] - previous.point[0]),
                 previous.point[1] + fraction * (point[1] - previous.point[1]))
        projection = ((cross[0] - self.start[0]) * self.dx + (cross[1] - self.start[1]) * self.dy) / self.length**2
        if not 0 <= projection <= 1:
            return None
        self.last_interval = (previous.observed_at, observed_at)
        return "negative_to_positive" if side > 0 else "positive_to_negative"
