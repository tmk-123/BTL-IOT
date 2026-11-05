"""Associate plates with unambiguous ByteTrack vehicles before temporal OCR voting."""

from dataclasses import asdict
import math

from plate_consensus import PlateConsensus
from plate_detection import predict_with_vehicle_crops


def empty_plate(status='not_enabled'):
    return dict(plate_text=None, plate_status=status, plate_vote_share=None,
                plate_bbox=None, plate_ocr=[])


def contained_fraction(plate, vehicle):
    x1, y1, x2, y2 = plate
    area = max(0, x2-x1) * max(0, y2-y1)
    intersection = max(0, min(x2, vehicle[2])-max(x1, vehicle[0])) * max(0, min(y2, vehicle[3])-max(y1, vehicle[1]))
    return intersection / area if area else 0


class VehiclePlateReader:
    def __init__(self, model, max_gap=0.5):
        self.model = model
        self.max_gap = max_gap
        self.states = {}
        self.previous_time = -math.inf
        self.scene_consensus = PlateConsensus(max_gap=max_gap)
        self.scene_tracks = []

    def reset(self):
        self.states.clear()
        self.scene_consensus = PlateConsensus(max_gap=self.max_gap)
        self.scene_tracks = []
        self.previous_time = -math.inf

    def update(self, frame, vehicles, timestamp):
        if not math.isfinite(timestamp) or timestamp < self.previous_time:
            raise ValueError('OCR timestamps must be finite and non-decreasing')
        self.previous_time = timestamp
        self.states = {key: value for key, value in self.states.items() if timestamp-value[0] <= self.max_gap}
        # Read the complete frame even when the vehicle model misses a toy car.
        # Scene votes are display-only; event OCR must still belong to a vehicle ID.
        predictions = predict_with_vehicle_crops(self.model, frame, [v['bbox'] for v in vehicles])
        raw = [asdict(result) for result in predictions]
        self.scene_tracks = self.scene_consensus.update(raw, timestamp)
        grouped = {vehicle['track_id']: [] for vehicle in vehicles}
        ambiguous = set()
        for plate in raw:
            box = plate['detection']['bounding_box']
            coordinates = [box[key] for key in ('x1', 'y1', 'x2', 'y2')]
            owners = [vehicle['track_id'] for vehicle in vehicles
                      if contained_fraction(coordinates, vehicle['bbox']) >= 0.9]
            if len(owners) == 1:
                grouped[owners[0]].append(plate)
            elif len(owners) > 1:
                ambiguous.update(owners)
        output = {}
        for vehicle in vehicles:
            identity = vehicle['track_id']
            candidates = grouped[identity]
            if identity in ambiguous or len(candidates) > 1:
                self.states.pop(identity, None)
                output[identity] = empty_plate('ambiguous')
                output[identity]['plate_ocr'] = candidates
                continue
            tracker = self.states.get(identity, (None, None))[1] or PlateConsensus(max_gap=self.max_gap)
            self.states[identity] = (timestamp, tracker)
            tracked = tracker.update(candidates, timestamp)
            if not tracked:
                output[identity] = empty_plate('no_plate')
                continue
            result = tracked[0]
            output[identity] = dict(plate_text=result['stable_text'], plate_status=result['status'],
                                    plate_vote_share=result['share'], plate_bbox=result['box'],
                                    plate_ocr=candidates)
        return output
