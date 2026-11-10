"""Detect vehicles in a local image/video or ESP32-CAM HTTP input."""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import time
from uuid import uuid4
from urllib.parse import urlparse

import cv2
import numpy as np
from ultralytics import YOLO

from camera_viewer import SnapshotCapture
from line_crossing import LineCrossing
from line_selector import select_line
from mqtt_light import add_mqtt_arguments, from_arguments
from light_state import SUSPECTED_ASSESSMENTS, assess_crossing
from event_store import EventStore
from vehicle_plate import VehiclePlateReader, empty_plate

ROOT = Path(__file__).resolve().parents[1]
VEHICLES = {"bicycle", "car", "motorcycle", "bus", "truck"}


def save_image(folder, frame):
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"vehicles_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg"
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise OSError("Cannot encode JPEG")
    encoded.tofile(str(target))
    print(f"Saved: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Local image/video path or HTTP URL")
    parser.add_argument("--snapshot", action="store_true", help="Repeated JPEG requests to http://<IP>/capture")
    parser.add_argument('--async-snapshot', action='store_true',
                        help='Fetch latest snapshots while AI runs; keeps receive timestamps and resets history after outages')
    parser.add_argument("--model", default=str(ROOT / "models" / "yolov8n.pt"))
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "detections")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "traffic.db")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "data" / "evidence")
    parser.add_argument("--save-all-evidence", action="store_true", help="Save images for all crossings, including UNKNOWN (for testing)")
    parser.add_argument("--no-display", action="store_true", help="Run without a preview window")
    parser.add_argument("--max-frames", type=int, default=0, help="0 processes until EOF or Q")
    parser.add_argument("--save-last", action="store_true", help="Save the last annotated frame on completion")
    parser.add_argument("--track", action="store_true", help="ByteTrack IDs and stop-line crossing events")
    parser.add_argument('--plate-ocr', action='store_true', help='Read plates per ByteTrack vehicle and store consensus at crossing')
    parser.add_argument('--plate-max-gap', type=float, default=0.5, help='OCR track expiry in seconds')
    parser.add_argument('--simulation', action='store_true', help='Mark every event as simulated; default to isolated demo storage')
    parser.add_argument("--select-line", action="store_true", help="Click two endpoints on the first frame; enables --track")
    parser.add_argument("--line", type=float, nargs=4, default=[0.15, 0.6, 0.85, 0.6],
                        metavar=("X1", "Y1", "X2", "Y2"), help="Normalized line endpoints (0..1)")
    parser.add_argument("--line-margin", type=float, default=5, help="Pixel deadband around line")
    parser.add_argument("--max-gap", type=int, default=5, help="Max frame-index gap for crossing continuity")
    parser.add_argument("--direction", choices=["both", "negative_to_positive", "positive_to_negative"], default="both")
    parser.add_argument("--violation-direction", choices=["both", "negative_to_positive", "positive_to_negative"],
                        default="both", help="Default demo assesses every crossing; optionally restrict the approach direction")
    parser.add_argument("--timing-margin", type=float, default=0.5, help="Extra lookback seconds for camera/network timing uncertainty")
    add_mqtt_arguments(parser)
    args = parser.parse_args()
    if args.simulation:
        demo = ROOT / 'data/demos/live_simulation'
        if args.database == ROOT / 'data/traffic.db': args.database = demo / 'traffic.db'
        if args.evidence_dir == ROOT / 'data/evidence': args.evidence_dir = demo / 'evidence'
        if args.output == ROOT / 'data/detections': args.output = demo / 'logs'
        if args.database.resolve() == (ROOT / 'data/traffic.db').resolve():
            parser.error('Simulation must use a separate demo database')
    if (args.mqtt_topic.startswith('demo/') or args.mqtt_device.startswith('simulation-')) and not args.simulation:
        parser.error('Demo lamp topics/devices require --simulation')
    if args.select_line:
        args.track = True
        if args.no_display:
            parser.error("--select-line needs a display; remove --no-display")
    if args.plate_ocr and not args.track:
        parser.error('--plate-ocr requires --track or --select-line')
    if not 0 < args.plate_max_gap < float('inf'):
        parser.error('--plate-max-gap must be finite and > 0')
    if not 0 < args.conf <= 1 or args.imgsz < 32 or args.max_frames < 0:
        parser.error("Require 0 < conf <= 1, imgsz >= 32 and max-frames >= 0")
    if any(not 0 <= value <= 1 for value in args.line) or args.line[:2] == args.line[2:]:
        parser.error("--line needs different endpoints within 0..1")
    if not 0 <= args.line_margin < float("inf") or args.max_gap < 1:
        parser.error("Require finite line-margin >= 0 and max-gap >= 1")
    remote = urlparse(args.source).scheme in ("http", "https")
    if args.mqtt_host and (not remote or not args.track):
        parser.error("Live MQTT requires a camera HTTP source and --track or --select-line; do not pair it with prerecorded video")
    if not 0 <= args.timing_margin < float("inf") or not 0 < args.light_timeout < float("inf") or not 1 <= args.mqtt_port <= 65535:
        parser.error("Invalid timing-margin, light-timeout or MQTT port")
    if args.snapshot and not remote:
        parser.error("--snapshot requires an HTTP URL ending in /capture")
    if args.async_snapshot and not args.snapshot:
        parser.error('--async-snapshot requires --snapshot')
    path = Path(args.source)
    if not remote and not path.is_file():
        parser.error(f"Input file does not exist: {path}")
    image = not remote and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if image and args.track:
        parser.error("Tracking needs video or camera frames, not a standalone image")
    cap = None
    preview = None
    count = 0
    detected = 0
    elapsed = 0.0
    crossing = None
    frame_size = None
    crossings = 0
    suspected = 0
    camera_failures = 0
    receiver = None
    store = None
    session_id = uuid4().hex
    event_path = args.output / f"crossings_{session_id}.jsonl"
    window = "YOLO vehicles | S: save | Q: quit"
    try:
        Path(args.model).parent.mkdir(parents=True, exist_ok=True)
        print(f"Loading {args.model} (first run may download weights)...")
        model = YOLO(args.model)
        plate_reader = None
        if args.plate_ocr:
            from plate_scanner import make_model, draw_consensus
            plate_reader = VehiclePlateReader(make_model(0.4), args.plate_max_gap)
        receiver = from_arguments(args)
        if receiver:
            receiver.start()
        classes = [key for key, value in model.names.items() if value in VEHICLES]
        if not classes:
            raise ValueError("Model has no supported vehicle classes")
        if not image:
            if args.snapshot:
                if args.async_snapshot:
                    from latest_capture import LatestSnapshotCapture
                    cap = LatestSnapshotCapture(args.source)
                else:
                    cap = SnapshotCapture(args.source)
            else:
                cap = cv2.VideoCapture()
                if remote:
                    opened = cap.open(args.source, cv2.CAP_FFMPEG, [
                        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
                        cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000,
                    ])
                else:
                    opened = cap.open(str(path))
                if not opened:
                    raise OSError("Cannot open source; check path/IP. For ESP32-CAM try --snapshot with /capture.")
        video_fps = cap.get(cv2.CAP_PROP_FPS) if not remote and not image else None
        if plate_reader and not remote and (video_fps is None or not 0 < video_fps < float('inf')):
            raise ValueError('Video FPS is required for OCR temporal voting')
        if not args.no_display:
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        if args.track:
            store = EventStore(args.database, args.evidence_dir)
            print(f"SQLite: {store.database}; evidence: {store.evidence_dir}")
        while True:
            started = time.perf_counter()
            if image:
                frame = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
                ok = frame is not None
            else:
                ok, frame = cap.read()
            if not ok:
                if remote and args.snapshot:
                    camera_failures += 1
                    # Never bridge a crossing or OCR votes across a camera outage.
                    crossing = None
                    if plate_reader is not None:
                        plate_reader.reset()
                    if camera_failures < 3:
                        print(f'Camera read failed; retrying ({camera_failures}/3). Crossing history reset.', flush=True)
                        time.sleep(.3)
                        continue
                if remote or image or count == 0:
                    raise OSError("Cannot read frame; camera disconnected or input cannot be decoded")
                print("End of video.")
                break
            camera_failures = 0
            if args.async_snapshot:
                observed_at, observed_mono = cap.observed_at, cap.observed_mono
                if cap.discontinuity:
                    crossing = None
                    if plate_reader is not None:
                        plate_reader.reset()
                    print('Snapshot interruption recovered. Crossing/OCR history reset.', flush=True)
            else:
                observed_at = datetime.now().astimezone().isoformat()
                observed_mono = time.monotonic()
            if args.select_line:
                chosen = select_line(frame, read_frame=cap.read if remote else None)
                if chosen is None:
                    print("Line selection cancelled. No tracking events recorded.")
                    return 0
                args.line = chosen
                args.select_line = False
                print("Reuse this line next run: --track --line " + " ".join(f"{v:.6f}" for v in chosen))
                if remote:
                    # Fetch a fresh camera frame after time spent on the selection screen.
                    continue
                started = time.perf_counter()
            frame_index = count + 1
            if args.track:
                result = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=classes,
                                     conf=args.conf, imgsz=args.imgsz, device=args.device, verbose=False)[0]
            else:
                result = model.predict(frame, classes=classes, conf=args.conf,
                                       imgsz=args.imgsz, device=args.device, verbose=False)[0]
            preview = result.plot()
            vehicles = []
            if args.track and result.boxes.id is not None:
                vehicles = [dict(bbox=box, track_id=identity) for box, identity in zip(
                    result.boxes.xyxy.cpu().tolist(), result.boxes.id.int().cpu().tolist())]
            plate_results = plate_reader.update(frame, vehicles, observed_mono if remote else (frame_index-1)/video_fps) if plate_reader else {}
            if plate_reader:
                preview = draw_consensus(preview, plate_reader.scene_tracks)
                if not vehicles:
                    cv2.putText(preview, 'No tracked vehicle: plate OCR only; crossing unavailable',
                                (10, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 180, 255), 2)
            for vehicle in vehicles:
                plate = plate_results.get(vehicle['track_id'])
                if plate:
                    x, y = round(vehicle['bbox'][0]), max(100, round(vehicle['bbox'][1])+25)
                    cv2.putText(preview, f"Plate: {plate['plate_text'] or plate['plate_status']}", (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
            if args.track:
                height, width = frame.shape[:2]
                if frame_size is not None and frame_size != (width, height):
                    raise ValueError("Frame resolution changed; restart tracking with a new line")
                frame_size = (width, height)
                start = (round(args.line[0] * (width - 1)), round(args.line[1] * (height - 1)))
                end = (round(args.line[2] * (width - 1)), round(args.line[3] * (height - 1)))
                if crossing is None:
                    crossing = LineCrossing(start, end, args.line_margin, args.max_gap)
                    print(f"Stop line pixels: {start} -> {end}; events: {event_path}")
                crossing.expire(frame_index)
                cv2.line(preview, start, end, (0, 255, 255), 2)
                if result.boxes.id is not None:
                    for box, track_id, cls, confidence in zip(result.boxes.xyxy.cpu().tolist(),
                            result.boxes.id.int().cpu().tolist(), result.boxes.cls.int().cpu().tolist(),
                            result.boxes.conf.cpu().tolist()):
                        point = ((box[0] + box[2]) / 2, box[3])
                        cv2.circle(preview, (round(point[0]), round(point[1])), 4, (0, 255, 255), -1)
                        direction = crossing.update(track_id, point, frame_index, observed_mono)
                        if direction and args.direction in ("both", direction):
                            crossings += 1
                            interval_start, interval_end = crossing.last_interval
                            decision = assess_crossing(
                                receiver.state if receiver else None,
                                interval_start, interval_end, direction,
                                args.violation_direction, args.timing_margin)
                            light_state, assessment = decision["light_state"], decision["assessment"]
                            suspected += assessment in SUSPECTED_ASSESSMENTS
                            video_ms = cap.get(cv2.CAP_PROP_POS_MSEC) if not remote else None
                            event = {"event_id": f"{session_id}:{frame_index}:{track_id}",
                                     "session_id": session_id, "frame": frame_index, "track_id": track_id,
                                     "vehicle_class": model.names[cls], "confidence": confidence,
                                     "direction": direction, "anchor": list(point),
                                     "bbox": box,
                                     "line_pixels": [list(start), list(end)],
                                     "observed_at": observed_at, "source": args.source,
                                     "video_time_ms": video_ms, "light_state": light_state,
                                     "assessment": assessment, "assessment_reason": decision["assessment_reason"],
                                     "timing_margin_s": args.timing_margin,
                                     "crossing_window_s": interval_end - interval_start,
                                     "event_type": "line_crossing"}
                            if args.simulation:
                                event.update(simulation=True, simulation_kind='camera_with_synthetic_light')
                            event.update(plate_results.get(track_id, empty_plate()))
                            if plate_reader:
                                event['plate_models'] = {'detector': 'yolo-v9-t-384-license-plate-end2end',
                                                         'ocr': 'cct-xs-v2-global-model'}
                            evidence = preview.copy()
                            if args.simulation:
                                cv2.putText(evidence, 'SIMULATION - not a real violation', (10, 105),
                                            cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 255, 255), 2)
                            cv2.putText(evidence, f"ID {track_id} | {light_state} | {assessment}", (10, 25),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            event, inserted = store.save(event, frame, evidence, save_all=args.save_all_evidence)
                            args.output.mkdir(parents=True, exist_ok=True)
                            with event_path.open("a", encoding="utf-8") as events:
                                events.write(json.dumps(event, ensure_ascii=False) + "\n")
                            print(f"CROSSING #{crossings}: ID {track_id} {model.names[cls]} {direction} | {light_state} | {assessment} | {decision['assessment_reason']}")
                live_light = receiver.state.current() if receiver else "UNKNOWN"
                cv2.putText(preview, f"Crossings: {crossings} | Light: {live_light}", (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(preview, f"Suspected red/yellow-light: {suspected}", (10, 75),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
                if args.simulation:
                    cv2.putText(preview, 'SIMULATION - synthetic light', (10, 105),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
            duration = time.perf_counter() - started
            elapsed += duration
            count += 1
            detected += len(result.boxes)
            cv2.putText(preview, f"FPS: {1 / max(duration, 1e-6):.1f} | Vehicles: {len(result.boxes)}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if count == 1:
                print(f"First frame: {len(result.boxes)} vehicle(s). S saves annotated image; Q exits.")
            if not args.no_display:
                cv2.imshow(window, preview)
                key = cv2.waitKey(0 if image else 1) & 0xFF
                if key in (ord("s"), ord("S")):
                    save_image(args.output, preview)
                if key in (ord("q"), ord("Q"), 27) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                    break
            if image or (args.max_frames and count >= args.max_frames):
                break
        if args.save_last and preview is not None:
            save_image(args.output, preview)
        print(f"Processed {count} frame(s), {detected} detections across frames, average FPS: {count / max(elapsed, 1e-6):.2f}")
        print("Detections are not unique vehicle counts or traffic violations.")
        if args.track:
            print(f"Crossings: {crossings}. Event file is created on first crossing: {event_path}")
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, sqlite3.Error, cv2.error) as exc:
        print(f"Detection failed: {exc}")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        if store is not None:
            store.close()
        if receiver is not None:
            receiver.stop()
        if cap is not None:
            cap.release()
        if not args.no_display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
