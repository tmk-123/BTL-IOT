"""Play a looping source video on screen for an ESP32-CAM to film physically."""

import argparse
import math
from pathlib import Path
import time
import tkinter as tk

import cv2

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, default=ROOT / 'data/test_samples/vietnam/traffic_sample.MOV')
    parser.add_argument('--speed', type=float, default=0.5, help='Playback speed (0.5 = half speed)')
    parser.add_argument('--max-seconds', type=float, default=0, help='Auto-close after this many seconds; 0 keeps playing')
    args = parser.parse_args()
    if not math.isfinite(args.speed) or args.speed <= 0 or not math.isfinite(args.max_seconds) or args.max_seconds < 0:
        parser.error('Require finite speed > 0 and max-seconds >= 0')
    cap = cv2.VideoCapture(str(args.video))
    window = None
    try:
        if not cap.isOpened():
            raise OSError(f'Cannot open video: {args.video}')
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError('Cannot determine video FPS')
        interval = 1 / (fps * args.speed)
        window = tk.Tk()
        window.title('Video cho ESP32-CAM | Space: tam dung | F: toan man hinh | R: tu dau | Q: thoat')
        width = min(1280, max(480, window.winfo_screenwidth()-660))
        height = min(800, window.winfo_screenheight()-120)
        window.geometry(f'{width}x{height}+0+0')
        window.configure(background='black')
        label = tk.Label(window, background='black')
        label.pack(fill='both', expand=True)
        running, paused, fullscreen = True, False, False

        def quit_video(event=None):
            nonlocal running
            running = False

        def pause(event=None):
            nonlocal paused
            paused = not paused

        def toggle_fullscreen(event=None):
            nonlocal fullscreen
            fullscreen = not fullscreen
            window.attributes('-fullscreen', fullscreen)

        def restart(event=None):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        window.protocol('WM_DELETE_WINDOW', quit_video)
        for key in ('q', 'Q', '<Escape>'): window.bind(key, quit_video)
        for key in ('f', 'F'): window.bind(key, toggle_fullscreen)
        for key in ('r', 'R'): window.bind(key, restart)
        window.bind('<space>', pause)
        started = time.monotonic()
        print('Source video playing in a loop. Point ESP32-CAM at this window.', flush=True)
        print('Space: pause/resume | F: fullscreen | R: restart | Q: quit', flush=True)
        while running:
            tick = time.monotonic()
            window.update()
            if not running or (args.max_seconds and tick-started >= args.max_seconds):
                break
            if not paused:
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = cap.read()
                    if not ok:
                        raise OSError('Video has no decodable frames')
                h, w = frame.shape[:2]
                scale = min(max(1, label.winfo_width())/w, max(1, label.winfo_height())/h)
                preview = cv2.resize(frame, (max(1, round(w*scale)), max(1, round(h*scale))))
                ok, png = cv2.imencode('.png', preview)
                if not ok:
                    raise OSError('Cannot encode video preview')
                photo = tk.PhotoImage(data=png.tobytes())
                label.configure(image=photo)
                label.image = photo
            time.sleep(max(0.001, interval-(time.monotonic()-tick)))
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, cv2.error, tk.TclError) as error:
        print(f'Video playback error: {error}')
        return 1
    finally:
        cap.release()
        if window:
            window.destroy()


if __name__ == '__main__':
    raise SystemExit(main())
