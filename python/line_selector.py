"""Choose normalized stop-line endpoints on a frozen frame."""

import cv2


def select_line(frame):
    height, width = frame.shape[:2]
    scale = min(1000 / width, 700 / height, 1.0)
    display = cv2.resize(frame, (max(2, round(width * scale)), max(2, round(height * scale))))
    points = []
    window = "Stop line | Click 2 points | Enter: confirm | R: reset | Q: cancel"

    def on_mouse(event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            if 0 <= x < display.shape[1] and 0 <= y < display.shape[0]:
                points.append((x, y))

    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window, on_mouse)
    print("Click the two ends of the stop line. Enter confirms; R resets; Q cancels.")
    try:
        while True:
            preview = display.copy()
            for point in points:
                cv2.circle(preview, point, 5, (0, 255, 255), -1)
            if len(points) == 2:
                cv2.line(preview, points[0], points[1], (0, 255, 255), 2)
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
