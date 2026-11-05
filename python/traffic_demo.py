"""Interactive simulated traffic lamps with a real HTTP camera and stop-line picker."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
from urllib.parse import urlparse

from simulated_light import SimulatedLight

ROOT = Path(__file__).resolve().parents[1]


def camera_command(source, output, port, topic, device, plate_ocr=True, select_line=True):
    parsed = urlparse(source)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Camera URL must start with http:// or https://')
    if parsed.path in ('', '/'):
        source = source.rstrip('/')+'/capture'
    args = [sys.executable, '-u', '-B', str(ROOT/'python/vehicle_detector.py'), '--source', source,
            '--snapshot', '--track', '--simulation', '--save-all-evidence',
            '--database', str(output/'traffic.db'), '--evidence-dir', str(output/'evidence'),
            '--output', str(output/'logs'), '--mqtt-host', '127.0.0.1', '--mqtt-port', str(port),
            '--mqtt-topic', topic, '--mqtt-device', device, '--plate-max-gap', '1.5']
    if select_line: args.append('--select-line')
    if plate_ocr: args.append('--plate-ocr')
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera-url', default='http://10.82.212.69/capture')
    parser.add_argument('--auto-start', action='store_true', help='Open camera and line picker immediately')
    parser.add_argument('--max-seconds', type=float, default=0, help='Auto-close control panel; 0 keeps it open')
    args = parser.parse_args()
    output = ROOT/'data/demos/live_simulation'
    light = None
    window = None
    child = None
    child_log = None
    try:
        light = SimulatedLight(output)
        window = tk.Tk()
        window.title('Mô phỏng giao thông — KHÔNG dùng đèn thật')
        window.geometry('580x510+20+20')
        window.configure(background='#f1f5f9')
        tk.Label(window, text='ĐÈN GIAO THÔNG GIẢ LẬP', font=('Segoe UI', 18, 'bold'), bg='#f1f5f9').pack(pady=(18, 4))
        tk.Label(window, text='Camera thật · Vạch tự chọn · Dữ liệu thử lưu riêng', bg='#f1f5f9').pack()
        lamp = tk.Label(window, text='XANH', font=('Segoe UI', 30, 'bold'), bg='#16a34a', fg='white', width=15)
        lamp.pack(pady=14)
        notice = tk.StringVar(value='Bắt đầu bằng đèn xanh. Chọn vạch rồi phát video cho xe đi qua.')
        def switch(state):
            try:
                light.set_state(state)
                label, color = {'GREEN': ('XANH', '#16a34a'), 'RED': ('ĐỎ', '#dc2626'),
                                'YELLOW': ('VÀNG', '#a16207'), 'UNKNOWN': ('NGỪNG GỬI', '#475569')}[state]
                lamp.configure(text=label, bg=color)
                notice.set('Chờ ít nhất 2 giây trước khi xe qua vạch.' if state != 'UNKNOWN' else 'Ngừng heartbeat: bộ nhận sẽ về UNKNOWN khi hết hạn.')
            except Exception as error:
                notice.set(f'Lỗi đèn giả lập: {error}')
        buttons = tk.Frame(window, bg='#f1f5f9')
        buttons.pack()
        for label, state in [('Xanh', 'GREEN'), ('Đỏ', 'RED'), ('Vàng', 'YELLOW'), ('Ngừng gửi', 'UNKNOWN')]:
            tk.Button(buttons, text=label, width=12, command=lambda color=state: switch(color)).pack(side='left', padx=3)
        camera_url = tk.StringVar(value=args.camera_url)
        tk.Label(window, text='Địa chỉ ESP32-CAM', bg='#f1f5f9').pack(pady=(14, 3))
        tk.Entry(window, textvariable=camera_url, font=('Segoe UI', 11), width=52).pack()
        ocr = tk.BooleanVar(value=True)
        tk.Checkbutton(window, text='Đọc biển số (bỏ chọn để thử tracking nhanh hơn)', variable=ocr, bg='#f1f5f9').pack(pady=7)
        def start_camera():
            nonlocal child, child_log
            if child is not None and child.poll() is None:
                notice.set('Camera đang chạy. Chọn hai đầu vạch rồi Enter; Q để dừng cửa sổ camera.')
                return
            if child_log is not None: child_log.close()
            try:
                command = camera_command(camera_url.get().strip(), output, light.port, light.topic, light.device, ocr.get())
                log_path = output/f'camera_{light.session}.log'
                child_log = log_path.open('a', encoding='utf-8')
                child = subprocess.Popen(command, stdout=child_log, stderr=subprocess.STDOUT, cwd=ROOT,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                notice.set('Căn camera vào video trong cửa sổ chọn vạch. Click đầu tiên đóng băng ảnh; chọn đầu thứ hai rồi Enter.')
            except Exception as error:
                notice.set(f'Không mở được camera: {error}')
        tk.Button(window, text='Mở camera / chọn lại vạch', command=start_camera, font=('Segoe UI', 11, 'bold')).pack(pady=5)
        tk.Label(window, textvariable=notice, wraplength=530, bg='#f1f5f9', fg='#334155').pack(padx=15, pady=10)
        tk.Label(window, text='Xem kết quả trên Streamlit: chọn “Camera + đèn giả lập”.\nQ ở cửa sổ camera để dừng; đóng bảng này để tắt mô phỏng.',
                 bg='#f1f5f9', fg='#475569').pack()
        started = time.monotonic()
        def heartbeat():
            if args.max_seconds and time.monotonic()-started >= args.max_seconds:
                window.quit()
                return
            try:
                light.publish()
            except Exception as error:
                notice.set(f'Mất kết nối bộ giả lập: {error}')
            if child is not None and child.poll() is not None:
                notice.set(f'Cửa sổ camera đã dừng (mã {child.returncode}). Có thể mở lại; log: {output.name}/camera_{light.session}.log')
            window.after(500, heartbeat)
        window.after(100, heartbeat)
        if args.auto_start: window.after(500, start_camera)
        print(f'SIMULATION controller ready; broker loopback:{light.port}; topic={light.topic}', flush=True)
        window.mainloop()
        return 0
    except Exception as error:
        print(f'Cannot start traffic simulation: {error}', flush=True)
        return 1
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try: child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
        if child_log is not None: child_log.close()
        if light is not None: light.close()
        if window is not None:
            try: window.destroy()
            except tk.TclError: pass


if __name__ == '__main__':
    raise SystemExit(main())
