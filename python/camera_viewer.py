"""View the ESP32-CAM MJPEG stream; S saves an original frame, Q exits."""

import argparse
from datetime import datetime
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import ProxyHandler, build_opener

import cv2
import numpy as np


class SnapshotCapture:
    """Read successive JPEG snapshots when the MJPEG endpoint is unavailable."""

    def __init__(self, url):
        self.url = url
        self.opener = build_opener(ProxyHandler({}))

    def read(self):
        try:
            with self.opener.open(self.url, timeout=5) as response:
                data = response.read(5_000_001)
            if len(data) > 5_000_000:
                raise ValueError("Snapshot exceeds 5 MB")
            frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            return frame is not None, frame
        except (OSError, ValueError) as exc:
            print(f"Cannot read snapshot: {exc}")
            return False, None

    def release(self):
        self.opener.close()


def main():
    parser = argparse.ArgumentParser(description="ESP32-CAM -> OpenCV (S: save, Q: quit)")
    parser.add_argument("--url", required=True, help="Example: http://192.168.1.10:81/stream")
    parser.add_argument("--snapshot", action="store_true", help="Repeatedly fetch JPEGs; use --url http://<IP>/capture")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "snapshots")
    args = parser.parse_args()
    if urlparse(args.url).scheme not in ("http", "https") or not urlparse(args.url).hostname:
        parser.error("--url must be an HTTP stream URL")

    window = "ESP32-CAM | S: save | Q: quit"
    cap = SnapshotCapture(args.url) if args.snapshot else cv2.VideoCapture()
    try:
        print(f"Connecting: {args.url}")
        opened = args.snapshot or cap.open(args.url, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000,
        ])
        if not opened:
            print("Cannot open camera. Check power, IP, Wi-Fi and :81/stream URL.")
            return 1
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        print(f"Connected. Click the video window; S saves, Q exits.\nImages: {args.output.resolve()}")
        previous = time.monotonic()
        fps = 0.0
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("Stream interrupted or read timed out. Check camera and run again.")
                return 1
            now = time.monotonic()
            instant = 1 / max(now - previous, 0.000001)
            fps = instant if fps == 0 else 0.9 * fps + 0.1 * instant
            previous = now
            preview = frame.copy()
            cv2.putText(preview, f"FPS: {fps:.1f} | S: save | Q: quit", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow(window, preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in (ord("s"), ord("S")):
                try:
                    args.output.mkdir(parents=True, exist_ok=True)
                    target = args.output / f"camera_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg"
                    # imencode + tofile also supports Windows paths containing Vietnamese.
                    encoded_ok, encoded = cv2.imencode(".jpg", frame)
                    if not encoded_ok:
                        raise OSError("JPEG encoding failed")
                    encoded.tofile(str(target))
                    print(f"Saved: {target.resolve()}")
                except (OSError, cv2.error) as exc:
                    print(f"Cannot save image: {exc}")
        return 0
    except cv2.error as exc:
        print(f"OpenCV error: {exc}")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
