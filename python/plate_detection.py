"""Retry missed plates inside vehicle crops and keep full-frame coordinates."""

from dataclasses import replace
import math
from types import SimpleNamespace

import cv2


def coordinates(result):
    box = result.detection.bounding_box
    return box.x1, box.y1, box.x2, box.y2


def overlap_fraction(first, second):
    x1, y1 = max(first[0], second[0]), max(first[1], second[1])
    x2, y2 = min(first[2], second[2]), min(first[3], second[3])
    area = max(0, x2-x1) * max(0, y2-y1)
    smaller = min(max(0, first[2]-first[0]) * max(0, first[3]-first[1]),
                  max(0, second[2]-second[0]) * max(0, second[3]-second[1]))
    return area / smaller if smaller else 0


def predict_with_vehicle_crops(model, frame, vehicle_boxes):
    results = list(model.predict(frame))
    if frame is None:  # Test adapters may not supply an image.
        return results
    height, width = frame.shape[:2]
    for vehicle in vehicle_boxes:
        if len(vehicle) != 4 or not all(math.isfinite(v) for v in vehicle):
            continue
        x1, y1, x2, y2 = vehicle
        x1, y1 = max(0, min(width, math.floor(x1))), max(0, min(height, math.floor(y1)))
        x2, y2 = max(0, min(width, math.ceil(x2))), max(0, min(height, math.ceil(y2)))
        if x2 <= x1 or y2 <= y1:
            continue
        # Avoid repeated OCR if this vehicle already contains a detected plate.
        if any(_contained(coordinates(p), (x1, y1, x2, y2)) >= .9 for p in results):
            continue
        for plate in model.predict(frame[y1:y2, x1:x2].copy()):
            bx1, by1, bx2, by2 = coordinates(plate)
            box = (max(x1, min(x2, bx1+x1)), max(y1, min(y2, by1+y1)),
                   max(x1, min(x2, bx2+x1)), max(y1, min(y2, by2+y1)))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            if any(overlap_fraction(box, coordinates(p)) >= .7 for p in results):
                continue
            original_box = plate.detection.bounding_box
            mapped_box = replace(original_box, x1=box[0], y1=box[1], x2=box[2], y2=box[3])
            results.append(replace(plate, detection=replace(plate.detection, bounding_box=mapped_box)))
    return results


def _contained(plate, vehicle):
    area = max(0, plate[2]-plate[0]) * max(0, plate[3]-plate[1])
    intersection = max(0, min(plate[2], vehicle[2])-max(plate[0], vehicle[0])) * max(
        0, min(plate[3], vehicle[3])-max(plate[1], vehicle[1]))
    return intersection / area if area else 0


class VehicleCropPlateModel:
    """Standalone scanner adapter; integrated tracking reuses its existing boxes."""

    def __init__(self, model, vehicle_model):
        self.model, self.vehicle_model = model, vehicle_model
        self.classes = [key for key, name in vehicle_model.names.items()
                        if name in {'bicycle', 'car', 'motorcycle', 'bus', 'truck'}]

    def predict(self, frame):
        result = self.vehicle_model.predict(frame, classes=self.classes, conf=.35,
                                            device='cpu', verbose=False)[0]
        return predict_with_vehicle_crops(self.model, frame, result.boxes.xyxy.cpu().tolist())

    def draw_predictions(self, frame):
        results = self.predict(frame)
        image = frame.copy()
        for plate in results:
            x1, y1, x2, y2 = coordinates(plate)
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 220, 0), 2)
            if plate.ocr and plate.ocr.text:
                cv2.putText(image, plate.ocr.text, (x1, max(20, y1-8)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 220, 0), 2)
        return SimpleNamespace(image=image, results=results)
