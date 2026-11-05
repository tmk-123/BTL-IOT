"""Conservative spatial plate association and windowed OCR voting, independent of vehicle tracking."""

from collections import Counter, deque
from dataclasses import dataclass, field
import math
import re


def iou(a, b):
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union > 0 else 0


@dataclass
class PlateTrack:
    id: int
    box: tuple
    first_seen: float
    last_seen: float
    observations: int = 0
    votes: deque = field(default_factory=lambda: deque(maxlen=15))
    last_consensus: str | None = None
    transitions: list = field(default_factory=list)


class PlateConsensus:
    def __init__(self, max_gap=0.5, min_votes=5, min_share=0.6, min_confidence=0.8):
        self.max_gap = max_gap
        self.min_votes = min_votes
        self.min_share = min_share
        self.min_confidence = min_confidence
        self.active = {}
        self.finished = []
        self.next_id = 1
        self.previous_time = -math.inf

    def update(self, results, timestamp):
        if not math.isfinite(timestamp) or timestamp < self.previous_time:
            raise ValueError("Plate timestamps must be finite and non-decreasing")
        self.previous_time = timestamp
        for identity, track in list(self.active.items()):
            if timestamp - track.last_seen > self.max_gap:
                self.finished.append(self.describe(track))
                del self.active[identity]
        boxes = [tuple(row['detection']['bounding_box'][key] for key in ('x1', 'y1', 'x2', 'y2'))
                 for row in results]
        # Mutual best matches; ambiguous overlaps get new IDs instead of sharing votes.
        scores = {(index, identity): iou(box, track.box)
                  for index, box in enumerate(boxes) for identity, track in self.active.items()}
        matches = {}
        for index in range(len(boxes)):
            ranked = sorted(((score, identity) for (i, identity), score in scores.items() if i == index), reverse=True)
            if not ranked or ranked[0][0] < 0.15:
                continue
            score, identity = ranked[0]
            competing = sorted((value for (i, t), value in scores.items() if t == identity), reverse=True)
            if ((len(ranked) > 1 and ranked[1][0] >= score * 0.8)
                    or (len(competing) > 1 and competing[1] >= score * 0.8)
                    or score < competing[0]):
                continue
            matches[index] = identity
        output = []
        for index, row in enumerate(results):
            identity = matches.get(index)
            if identity is None:
                identity = self.next_id
                self.next_id += 1
                self.active[identity] = PlateTrack(identity, boxes[index], timestamp, timestamp)
            track = self.active[identity]
            track.box = boxes[index]
            track.last_seen = timestamp
            track.observations += 1
            ocr = row.get('ocr') or {}
            text = re.sub(r'[^A-Z0-9]', '', (ocr.get('text') or '').upper())
            confidence = ocr.get('confidence', 0)
            # Use the weakest character, not padded-character averages.
            confidence = min(confidence) if isinstance(confidence, list) and confidence else confidence
            confidence = confidence if isinstance(confidence, (int, float)) and math.isfinite(confidence) else None
            # OCR plausibility only; letter position does not validate a country's legal plate format.
            # For example, 80-441 NN-02 must not be rejected because letters follow five digits.
            plausible = (6 <= len(text) <= 12 and sum(c.isdigit() for c in text) >= 4
                         and 1 <= sum(c.isalpha() for c in text) <= 4)
            if not text:
                observation_reason = 'empty_ocr'
            elif not plausible:
                observation_reason = 'unsupported_layout'
            elif confidence is None or confidence < self.min_confidence:
                observation_reason = 'low_confidence'
            else:
                observation_reason = None
            valid = observation_reason is None
            track.votes.append(text if valid else None)
            votes = Counter(value for value in track.votes if value)
            candidate, support = votes.most_common(1)[0] if votes else (None, 0)
            share = support / len(track.votes)
            accepted = support >= self.min_votes and share >= self.min_share
            stable = candidate if accepted else None
            pending_reason = None if stable else (observation_reason or (
                'not_enough_matches' if support < self.min_votes else 'readings_disagree'))
            if stable and stable != track.last_consensus:
                track.transitions.append({'time': timestamp, 'text': stable, 'votes': support,
                                          'window': len(track.votes), 'share': share})
                track.last_consensus = stable
            output.append({'track_id': identity, 'raw_text': ocr.get('text'), 'stable_text': stable,
                           'status': 'consensus' if stable else 'pending', 'votes': support,
                           'window': len(track.votes), 'share': round(share, 3),
                           'pending_reason': pending_reason, 'observation_reason': observation_reason,
                           'min_character_confidence': confidence,
                           'box': list(track.box)})
        return output

    @staticmethod
    def describe(track):
        return {'track_id': track.id, 'first_seen': track.first_seen, 'last_seen': track.last_seen,
                'observations': track.observations, 'last_consensus': track.last_consensus,
                'consensus_transitions': track.transitions}

    def summaries(self):
        return self.finished + [self.describe(track) for track in self.active.values()]
