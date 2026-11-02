# Nhận diện xe bằng YOLO

Chạy PowerShell tại thư mục gốc dự án. Python 3.12 và `.venv` đã được tạo trên máy hiện tại.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Video có sẵn

Đặt video giao thông vào `data/videos/traffic.mp4` (tự tạo thư mục nếu cần):

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source data/videos/traffic.mp4
```

Có thể truyền đường dẫn tuyệt đối, đặt trong dấu nháy kép nếu có khoảng trắng.

## Ảnh và camera

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source data/samples/bus.jpg
.\.venv\Scripts\python.exe python/vehicle_detector.py --source http://10.82.212.69/capture --snapshot
```

Thay IP khi camera đổi địa chỉ. Đóng chương trình camera khác trước khi chạy. Khi sửa được MJPEG, dùng `--source http://<IP>:81/stream` và bỏ `--snapshot`.

- S lưu ảnh có khung/nhãn vào `data/detections/`; Q, Escape hoặc đóng cửa sổ để thoát.
- Với ảnh tĩnh, nhấn phím để kết thúc; S lưu ảnh rồi kết thúc.
- Mặc định chạy CPU, model `models/yolov8n.pt`, confidence 0.35, kích thước đầu vào 640. Lần đầu cần Internet để tải trọng số nếu chưa có.
- Thử `--conf 0.5` để lọc kết quả yếu; `--imgsz 320` để đánh giá tốc độ với kích thước nhỏ hơn.
- Dùng `--model <duong_dan.pt>` để thử trọng số khác có nhãn COCO phù hợp.
- Chạy không mở cửa sổ: thêm `--no-display --max-frames 30 --save-last`.
- Nhãn gồm bicycle, car, motorcycle, bus, truck; chỉ số Vehicles là số phát hiện trong frame hiện tại. Tổng detections cuối chương trình có thể đếm cùng xe ở nhiều frame.
- FPS đo cả đọc ảnh và xử lý, gồm chi phí khởi động suy luận ở frame đầu; không phải độ trễ truyền hình.

## Kiểm thử thực tế

1. Dùng video/ảnh có xe, kiểm tra khung bám xe và nhãn/confidence.
2. Thử cảnh không có xe, xe nhỏ/che khuất; ghi lại bỏ sót và nhận nhầm.
3. Nhấn S, mở JPG; Q rồi chạy lại. Với video, kiểm tra chạy đến cuối tự thoát.
4. Với camera, thử ngắt nguồn: chương trình cần báo lỗi sau timeout.
5. Ghi FPS và chất lượng trên video của nhóm; model huấn luyện xe thật có thể không nhận xe đồ chơi/carton.

Mặc định là detection. Thêm `--track` để bật [ByteTrack và vạch dừng](TRACKING.md). Chưa ghép MQTT, OCR hoặc kết luận vượt đèn đỏ.

## Model và giấy phép

Kiểm thử ngày 02/11/2026: Ultralytics 8.4.198, PyTorch 2.15.0, Python 3.12 CPU. Ảnh bus mẫu phát hiện 1 bus (confidence khoảng 0.88), lưu JPG có khung thành công. Video AVI tạo từ ảnh bus lặp 5 frame: đọc đủ 5 frame, 5 detections và tự thoát ở cuối video; đây không phải kiểm thử chuyển động/tracking. Camera thật `/capture`: đọc và suy luận 3 frame, 0 detections, lưu ảnh thành công; chưa có xe mô hình để đánh giá. `pip check` không phát hiện xung đột. Chưa kiểm thử thao tác bàn phím/cửa sổ của chương trình YOLO hoặc ngắt nguồn camera. FPS khởi động thấp, chưa dùng làm kết luận tốc độ ổn định.

YOLOv8n là cấu hình thử, chưa chốt model cuối cùng. So với model lớn, bắt đầu với bản nano để đánh giá trên CPU; đổi trọng số nếu chất lượng/tốc độ không đạt.

- Tài liệu chính thức: https://docs.ultralytics.com/models/yolov8/
- Giấy phép mã nguồn/trọng số: AGPL-3.0 hoặc Enterprise theo Ultralytics: https://www.ultralytics.com/license
- Model pretrained dùng COCO; thông tin dữ liệu/điều khoản: https://docs.ultralytics.com/datasets/detect/coco/ và https://cocodataset.org/#termsofuse
- Ảnh mẫu bus lấy từ https://github.com/ultralytics/assets/blob/main/im/bus.jpg chỉ để kiểm thử; không đưa ảnh, trọng số hay dữ liệu thử vào Git.
