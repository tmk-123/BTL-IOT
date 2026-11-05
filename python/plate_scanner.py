"""Local CPU plate detection + OCR. Tk preview also works with headless OpenCV."""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime
import json
import math
from pathlib import Path
import queue
import threading
import time
from urllib.parse import urlparse
from camera_viewer import SnapshotCapture
from plate_consensus import PlateConsensus
from plate_autosave import PlateAutoSaver

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DETECTOR = "yolo-v9-t-384-license-plate-end2end"
OCR = "cct-xs-v2-global-model"
PENDING_REASONS = {'empty_ocr': 'OCR has no text', 'unsupported_layout': 'text layout rejected',
                   'low_confidence': 'OCR confidence too low', 'not_enough_matches': 'waiting for matching reads',
                   'readings_disagree': 'OCR readings disagree'}


def make_model(confidence, vehicle_crops=False):
    from fast_alpr import ALPR

    model = ALPR(detector_model=DETECTOR, ocr_model=OCR,
                detector_conf_thresh=confidence, ocr_device="cpu",
                detector_providers=["CPUExecutionProvider"])
    if vehicle_crops:
        from ultralytics import YOLO
        from plate_detection import VehicleCropPlateModel
        model = VehicleCropPlateModel(model, YOLO(str(ROOT / 'models/yolov8n.pt')))
    return model


def save_result(frame, preview, results, output, source, tracks=None, *, target=None):
    target = target or output / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target.mkdir(parents=True, exist_ok=False)
    images = {"frame.jpg": frame, "annotated.jpg": preview}
    for index, result in enumerate(results):
        box = result.detection.bounding_box
        crop = frame[max(0, box.y1):min(frame.shape[0], box.y2),
                     max(0, box.x1):min(frame.shape[1], box.x2)]
        if crop.size:
            images[f"plate_{index}.jpg"] = crop
    for name, image in images.items():
        ok, encoded = cv2.imencode(".jpg", image)
        if not ok:
            raise OSError(f"Cannot encode {name}")
        encoded.tofile(str(target / name))
    metadata = {"time": datetime.now().astimezone().isoformat(),
                "source": source, "detector": DETECTOR, "ocr": OCR,
                "results": [asdict(result) for result in results]}
    if tracks is not None:
        metadata['plate_tracks'] = tracks
    (target / "result.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {target}")
    return target


def draw_consensus(frame, tracks):
    preview = frame.copy()
    for track in tracks:
        x1, y1, x2, y2 = track['box']
        color = (0, 220, 0) if track['stable_text'] else (0, 180, 255)
        cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
        lines = [f"#{track['track_id']} {track['stable_text'] or 'PENDING'} ({track['votes']}/{track['window']})",
                 f"raw: {track['raw_text'] or '?'}"]
        if not track['stable_text']:
            reason = PENDING_REASONS.get(track.get('pending_reason'), 'waiting for matching reads')
            confidence = track.get('min_character_confidence')
            lines.append(reason + (f' | min conf: {confidence:.2f}' if confidence is not None else ''))
        for index, line in enumerate(lines):
            y = max(22, y1 - 22 * len(lines)) + index * 22
            text_width = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0][0]
            x = max(0, min(x1, preview.shape[1] - text_width - 4))
            cv2.putText(preview, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4)
            cv2.putText(preview, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
    return preview


def scan_video(model, source, output, max_frames=0, stabilize=True):
    """Process files sequentially; retain every decoded frame and its OCR results."""
    if not source.is_file():
        raise OSError(f"Video does not exist: {source}")
    cap = cv2.VideoCapture(str(source))
    writer = None
    count = 0
    detected_frames = 0
    texts = Counter()
    interrupted = False
    consensus = PlateConsensus() if stabilize else None
    target = output / f"video_{datetime.now():%Y%m%d_%H%M%S_%f}"
    started = time.perf_counter()
    try:
        if not cap.isOpened():
            raise OSError(f"Cannot open video: {source}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Video FPS is unavailable; cannot preserve playback timing")
        target.mkdir(parents=True, exist_ok=False)
        with (target / "frames.jsonl").open("w", encoding="utf-8") as log:
            try:
                while not max_frames or count < max_frames:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    if writer is None:
                        height, width = frame.shape[:2]
                        writer = cv2.VideoWriter(str(target / "annotated.mp4"),
                                                 cv2.VideoWriter_fourcc(*"mp4v"), fps,
                                                 (width, height))
                        if not writer.isOpened():
                            raise OSError("Cannot create MP4 output")
                    prediction = model.draw_predictions(frame.copy())
                    results = prediction.results
                    raw = [asdict(r) for r in results]
                    tracks = consensus.update(raw, count / fps) if consensus else []
                    preview = draw_consensus(frame, tracks) if consensus else prediction.image
                    writer.write(preview)
                    log.write(json.dumps({"frame": count, "video_seconds": count / fps,
                                          "results": raw, "plate_tracks": tracks},
                                         ensure_ascii=False) + "\n")
                    if results:
                        detected_frames += 1
                        texts.update(r.ocr.text for r in results if r.ocr and r.ocr.text)
                        if detected_frames == 1:
                            save_result(frame, preview, results, target, str(source), tracks)
                    count += 1
                    if count % 100 == 0:
                        print(f"Processed {count} frames; {detected_frames} with plates", flush=True)
            except KeyboardInterrupt:
                interrupted = True
        if not count:
            raise OSError("Video contains no decodable frames")
        elapsed = time.perf_counter() - started
        summary = {"source": str(source.resolve()), "detector": DETECTOR, "ocr": OCR,
                   "frames_processed": count, "frames_with_plates": detected_frames,
                   "source_fps": fps, "video_seconds_processed": count / fps,
                   "processing_seconds": round(elapsed, 3),
                   "processing_fps": round(count / elapsed, 2),
                   "interrupted": interrupted, "max_frames": max_frames,
                   "ocr_text_frame_counts": dict(texts.most_common()),
                   "note": "Raw OCR counts across frames, not unique vehicles or accuracy. Output has no audio."}
        if consensus:
            tracks = consensus.summaries()
            (target / 'tracks.json').write_text(json.dumps(tracks, ensure_ascii=False, indent=2), encoding='utf-8')
            summary['plate_track_count'] = len(tracks)
            summary['tracks_with_consensus'] = sum(bool(track['last_consensus']) for track in tracks)
            summary['consensus_policy'] = {'window': 15, 'min_votes': 5, 'min_share': 0.6,
                                           'min_character_confidence': 0.8, 'max_gap_seconds': 0.5,
                                           'association': 'mutual best IoU >= 0.15; ambiguous matches split'}
        (target / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"Saved video and logs: {target.resolve()}", flush=True)
        return target
    finally:
        cap.release()
        if writer is not None:
            writer.release()


class LiveCamera:
    """Only retain the newest frame while CPU inference runs."""

    def __init__(self, source, snapshot=False):
        self.cap = SnapshotCapture(source) if snapshot else cv2.VideoCapture()
        self.frames = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.error = None
        self.failures = 0
        if snapshot:
            opened = True
        elif source.isdecimal():
            opened = self.cap.open(int(source), cv2.CAP_DSHOW)
            if opened:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        else:
            opened = self.cap.open(source, cv2.CAP_FFMPEG, [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000])
        if not opened:
            self.cap.release()
            raise OSError("Cannot open camera. Check index, IP, Wi-Fi and :81/stream.")
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        try:
            while not self.stop.is_set():
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    self.failures += 1
                    if self.failures >= 3:
                        self.error = "Camera stream interrupted after 3 failed reads. Check power/Wi-Fi and close other streams."
                        break
                    print(f"Camera read failed; retrying ({self.failures}/3)...", flush=True)
                    if self.stop.wait(0.3):
                        break
                    continue
                self.failures = 0
                try:
                    self.frames.get_nowait()
                except queue.Empty:
                    pass
                self.frames.put_nowait(frame)
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.cap.release()

    def close(self):
        self.stop.set()
        # Reader owns capture.release(); avoid releasing during a native read.
        self.thread.join(timeout=6)


def main():
    parser = argparse.ArgumentParser(description="Plate scanner: ESP32-CAM/webcam/image/video")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--source", help="0 for webcam, or http://IP:81/stream")
    source.add_argument("--image", type=Path, help="Run once, save JPG + JSON without a window")
    source.add_argument("--video", type=Path, help="Process video file; save annotated MP4 and per-frame JSONL")
    source.add_argument("--download-models", action="store_true", help="Download/cache models, then exit")
    parser.add_argument("--confidence", type=float, default=0.4)
    parser.add_argument('--vehicle-crops', action='store_true',
                        help='Retry missed plates in YOLO vehicle crops; requires the combined Python environment')
    parser.add_argument("--snapshot", action="store_true", help="Poll JPEG endpoint: --source http://IP/capture")
    parser.add_argument("--output", type=Path, help='Save folder; live camera defaults to data/plates')
    parser.add_argument('--no-auto-save', action='store_true', help='Disable automatic live camera saves; S still saves manually')
    parser.add_argument("--max-frames", type=int, default=0, help="Video frame limit; 0 processes the whole file")
    parser.add_argument("--raw-ocr", action="store_true", help="Disable temporal voting for video/camera comparison")
    parser.add_argument('--plate-max-gap', type=float, default=0.5, help='Camera OCR track expiry in seconds')
    args = parser.parse_args()
    args.output = args.output or ROOT / 'data' / ('plate_tests' if args.video or args.image else 'plates')
    if not 0 < args.confidence <= 1:
        parser.error("--confidence must be in (0, 1]")
    if not math.isfinite(args.plate_max_gap) or args.plate_max_gap <= 0:
        parser.error('--plate-max-gap must be finite and > 0')
    if args.plate_max_gap != 0.5 and (args.video or args.image or args.download_models):
        parser.error('--plate-max-gap is for live camera mode only')
    if args.max_frames < 0 or (args.max_frames and not args.video):
        parser.error("--max-frames requires --video and must be non-negative")
    camera_source = args.source or "0"
    if args.snapshot and (args.image or args.video or args.download_models or camera_source.isdecimal()):
        parser.error("--snapshot requires an HTTP(S) --source")
    if not camera_source.isdecimal():
        url = urlparse(camera_source)
        if url.scheme not in ("http", "https") or not url.hostname:
            parser.error("--source must be a webcam index or HTTP(S) stream URL")

    camera = None
    window = None
    try:
        print("Loading CPU models (first run downloads ~11 MB)...", flush=True)
        model = make_model(args.confidence, vehicle_crops=args.vehicle_crops)
        if args.download_models:
            print("Models ready. Cached under ~/.cache/open-image-models and ~/.cache/fast-plate-ocr.")
            return 0
        if args.video:
            scan_video(model, args.video, args.output, args.max_frames, not args.raw_ocr)
            return 0
        if args.image:
            frame = cv2.imdecode(np.fromfile(str(args.image), dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise OSError(f"Cannot read image: {args.image}")
            started = time.perf_counter()
            prediction = model.draw_predictions(frame.copy())
            print(f"Inference: {time.perf_counter() - started:.3f}s; plates: {len(prediction.results)}")
            save_result(frame, prediction.image, prediction.results, args.output, str(args.image))
            print(json.dumps([asdict(r) for r in prediction.results], ensure_ascii=False, indent=2))
            return 0

        import tkinter as tk

        camera = LiveCamera(camera_source, args.snapshot)
        window = tk.Tk()
        window.geometry(f'+{max(0, window.winfo_screenwidth()-650)}+0')
        window.title("Plate scanner | S: save | Q: quit")
        label = tk.Label(window)
        label.pack()
        status = tk.StringVar(value="Waiting for camera...")
        tk.Label(window, textvariable=status).pack()
        running = True
        current = None
        current_tracks = []
        # Track even in raw display mode so auto-save can avoid one file per frame.
        consensus = PlateConsensus(max_gap=args.plate_max_gap)
        auto_saver = None if args.no_auto_save else PlateAutoSaver(args.output, camera_source, save_result)
        print(f"Images: {args.output.resolve()} | auto-save: {'ON' if auto_saver else 'OFF'}", flush=True)
        saved_notice = ''
        saved_notice_until = 0

        def quit_window(event=None):
            nonlocal running
            running = False

        def save_current(event=None):
            if current is not None:
                try:
                    folder = save_result(*current, args.output, camera_source, current_tracks)
                    status.set(f"Saved: {folder.name}")
                except OSError as exc:
                    status.set(f"Save failed: {exc}")

        window.protocol("WM_DELETE_WINDOW", quit_window)
        for key in ("q", "Q", "<Escape>"):
            window.bind(key, quit_window)
        for key in ("s", "S"):
            window.bind(key, save_current)
        last_text = None
        while running:
            window.update()
            if camera.error:
                raise OSError(camera.error)
            try:
                frame = camera.frames.get(timeout=0.03)
            except queue.Empty:
                if camera.failures:
                    status.set(f'Camera connection interrupted; retrying ({camera.failures}/3)...')
                continue
            started = time.perf_counter()
            prediction = model.draw_predictions(frame.copy())
            current_tracks = consensus.update([asdict(r) for r in prediction.results], time.monotonic())
            annotated = draw_consensus(frame, current_tracks) if not args.raw_ocr else prediction.image
            current = (frame, annotated, prediction.results)
            if auto_saver:
                saved = auto_saver.update(frame, annotated, prediction.results, current_tracks)
                if saved:
                    saved_notice = f'Auto saved: {saved[-1].parent.name if saved[-1].name == "confirmed" else saved[-1].name}'
                    saved_notice_until = time.monotonic() + 4
            texts = ([f"#{t['track_id']} {t['stable_text'] or 'PENDING'}" for t in current_tracks]
                     if not args.raw_ocr else [r.ocr.text if r.ocr else "[unreadable]" for r in prediction.results])
            text = ", ".join(texts) or "No plate"
            if text != last_text:
                print(text, flush=True)
                last_text = text
            elapsed = time.perf_counter() - started
            save_status = saved_notice if time.monotonic() < saved_notice_until else f"Auto-save: {'ON' if auto_saver else 'OFF'}"
            status.set(f"{text} | AI: {elapsed * 1000:.0f} ms | {save_status} | S: save | Q: quit")
            preview = annotated
            height, width = preview.shape[:2]
            scale = min(1, 1100 / width, 750 / height)
            if scale < 1:
                preview = cv2.resize(preview, (int(width * scale), int(height * scale)))
            ok, png = cv2.imencode(".png", preview)
            if not ok:
                raise OSError("Cannot encode preview")
            photo = tk.PhotoImage(data=png.tobytes())
            label.configure(image=photo)
            label.image = photo
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        if camera:
            camera.close()
        if window:
            window.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
