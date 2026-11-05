"""Choose normalized stop-line endpoints on a frozen frame."""

import cv2


def select_line(frame, read_frame=None):
    height, width = frame.shape[:2]
    scale = min(1000 / width, 700 / height)
    display = cv2.resize(frame, (max(2, round(width * scale)), max(2, round(height * scale))))
    points = []
    window = "Stop line | Click 2 points | Enter: confirm | R: reset | Q: cancel"

    def on_mouse(event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            if 0 <= x < display.shape[1] and 0 <= y < display.shape[0]:
                points.append((x, y))

    cv2.namedWindow(window, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window, display.shape[1], display.shape[0])
    cv2.setMouseCallback(window, on_mouse)
    print("Align camera, then click two ends of the stop line. First click freezes the image; Enter confirms; R resets; Q cancels.")
    try:
        while True:
            if read_frame is not None and not points:
                ok, live = read_frame()
                if not ok or live is None:
                    raise OSError('Cannot read camera while selecting the stop line')
                if live.shape[:2] != frame.shape[:2]:
                    raise ValueError('Camera resolution changed while selecting line; restart selection')
                display = cv2.resize(live, (display.shape[1], display.shape[0]))
            preview = display.copy()
            for point in points:
                cv2.circle(preview, point, 5, (0, 255, 255), -1)
            if len(points) == 2:
                cv2.line(preview, points[0], points[1], (0, 255, 255), 2)
            if points:
                hint = "PAUSED - Enter: start detection | R: live camera / redraw"
            elif read_frame is not None:
                hint = "LIVE - Click two ends of stop line"
            else:
                hint = "Click two ends of stop line | Enter: confirm"
            cv2.rectangle(preview, (0, 0), (preview.shape[1], 32), (0, 0, 0), -1)
            cv2.putText(preview, hint, (8, 22), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow(window, preview)
            key = cv2.waitKey(20) & 0xFF
            if key in (ord("q"), ord("Q"), 27) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                return None
            if key in (ord("r"), ord("R")):
                points.clear()
            if key in (10, 13) and len(points) == 2:
                if points[0] == points[1]:
                    print("Choose two different endpoints; press R to reset.")
                    continue
                return [coordinate for x, y in points
                        for coordinate in (x / (display.shape[1] - 1), y / (display.shape[0] - 1))]
    finally:
        # The user may have already closed the selection window.
        try:
            cv2.destroyWindow(window)
        except cv2.error:
            pass
