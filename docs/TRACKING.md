# Tracking và vạch dừng

Chạy tại thư mục gốc repository, sau khi cài `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source "data/videos/traffic.mp4" --track
```

Camera thật (thay IP nếu đổi):

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source http://10.82.212.69/capture --snapshot --track
```

Đóng các chương trình khác đang đọc camera. Snapshot có tốc độ thấp và khoảng cách thời gian giữa các frame không đều, nên cần đánh giá độ ổn định ID bằng video trước. Ảnh tĩnh không hỗ trợ `--track`.

## Đặt vạch

### Bấm chuột chọn vạch (dễ dùng)

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source "data/videos/traffic.mp4" --select-line
```

`--select-line` tự bật tracking. Chương trình dừng ở hình đầu tiên:

1. Bấm chuột trái vào hai đầu của vạch dừng muốn đặt (nên chọn từ trái sang phải).
2. Nhấn Enter để xác nhận và bắt đầu chạy.
3. Nhấn R nếu muốn xóa hai điểm để chọn lại; Q/Escape để hủy.

Với camera: dùng `--source http://<IP>/capture --snapshot --select-line`. Camera phải gửi được ảnh trước khi chọn vạch; lựa chọn này không sửa lỗi timeout mạng.

Tọa độ được in trong terminal dưới dạng `--track --line ...` để dùng lại lần sau, chưa tự lưu cấu hình. Với video mẫu trên máy hiện tại, có thể thử:

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source data/samples/bus_moving.avi --select-line
```

Chọn vạch ngang khoảng 65% chiều cao để thấy điểm vàng của xe buýt qua vạch. Đây là ảnh dịch chuyển giả lập, không phải video giao thông thật. Video mẫu ngắn và tự đóng khi kết thúc.

### Nhập tọa độ

Vạch vàng mặc định từ `(15% chiều rộng, 60% chiều cao)` tới `(85% chiều rộng, 60% chiều cao)`.

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source "data/videos/traffic.mp4" --track --line 0.1 0.7 0.9 0.7
```

`--line X1 Y1 X2 Y2`: tọa độ theo tỷ lệ 0..1; gốc trên trái, X tăng sang phải, Y tăng xuống dưới. Ví dụ trên đặt vạch ngang ở 70% chiều cao. Đặt vạch trùng vị trí vạch dừng trong hình; đây là đường cấu hình, chưa tự nhận diện vạch trên mặt đường.

- ID hiển thị trên khung xe do ByteTrack cấp; dùng `persist=True` giữa các frame cùng nguồn.
- Chấm vàng ở giữa cạnh dưới khung xe là điểm dùng kiểm tra qua vạch; đây là quy ước hình học, cần chỉnh góc quay để phù hợp mô hình, chưa phải phép đo đầu xe thật.
- Xe đổi từ một phía ổn định sang phía kia và đường đi cắt đoạn vạch mới tạo sự kiện. Không đếm phần kéo dài ngoài hai đầu vạch.
- `--line-margin 5`: bỏ qua dải cách đường tối đa 5 pixel mỗi phía để hạn chế rung quanh vạch. Xe chạm vạch rồi lùi về phía cũ không được đếm.
- `--max-gap 5`: chỉ nối vị trí nếu chênh lệch chỉ số frame không quá 5. Xe mất tracking lâu hoặc đổi ID phải lấy lại phía ban đầu; có thể bỏ sót qua vạch, không tự suy diễn.
- Đi ngược trở lại rồi qua lần nữa được tính là lượt khác. ID không bảo đảm giữ nguyên khi che khuất; không cam kết chống trùng giữa các ID khác nhau hoặc sau khi khởi động lại.

## Hướng đi và log

`--direction both` đếm hai chiều. Với vạch ngang vẽ từ trái sang phải:

- `--direction negative_to_positive`: từ trên xuống dưới.
- `--direction positive_to_negative`: từ dưới lên trên.

Đảo hai đầu vạch sẽ đảo nghĩa hai phía. Với vạch chéo, hai phía dựa trên dấu tích có hướng của vector vạch và vector từ đầu vạch tới điểm xe.

Mỗi lần qua được in `CROSSING ...`; tổng hiện ở góc màn hình. S lưu ảnh có ID/vạch, Q thoát.

Log tự tạo khi có sự kiện đầu tiên: `data/detections/crossings_<session>.jsonl`. Mỗi dòng chứa ID sự kiện/phiên chạy, ID xe, loại xe, confidence, hướng, frame, điểm kiểm tra, vạch, nguồn và thời gian. Đã bổ sung SQLite và tự lưu ảnh cho trường hợp nghi vượt đèn đỏ theo [STORAGE.md](STORAGE.md); JSONL tiếp tục làm log phụ.

`observed_at` là thời điểm laptop nhận frame xác nhận đổi phía; `video_time_ms` là vị trí frame trong video file (nếu backend hỗ trợ), không phải thời gian xe thực đi qua vạch. Deadband làm xác nhận chậm hơn giao điểm thực. Không dùng timestamp này để kết luận vượt đèn khi chưa đánh giá đồng bộ thời gian.

Không bật MQTT thì `light_state` là `UNKNOWN`. Đã thêm bộ nhận và ghép đèn theo [MQTT_PYTHON.md](MQTT_PYTHON.md); khi có dữ liệu phù hợp, JSONL bổ sung `assessment` để đánh dấu nghi vượt đèn đỏ. Loại sự kiện gốc vẫn là `line_crossing`, cần kiểm tra lại và chưa xác nhận toàn luồng trên mạch thật.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Ngày 02/11/2026:

- 11 kiểm thử hình học đạt: đứng yên, dải chống rung, hai hướng, lượt quay lại, ngoài đoạn vạch, vạch đứng/chéo, mất ID/khoảng trống dài và dọn trạng thái.
- Video ảnh bus đứng yên 5 frame: chạy ByteTrack, 0 crossing.
- Video tổng hợp 41 frame dịch chuyển ảnh bus: nhận 41 detections, giữ ID 1, ghi đúng 1 crossing `negative_to_positive`, lưu JPG và kiểm tra JSONL thành công. Tốc độ trung bình khoảng 12 FPS trên lần chạy này; không đại diện video thực.
- Cần kiểm tra thêm video giao thông của nhóm, nhiều xe/che khuất và thao tác cửa sổ/bàn phím. Video tổng hợp không thay thế đánh giá xe mô hình thật.
- Bổ sung chọn vạch bằng chuột: đã kiểm tra CLI và chạy lại 11 kiểm thử logic; thao tác chuột/Enter trên cửa sổ cần người dùng thử trực tiếp.

API ByteTrack chính thức: https://docs.ultralytics.com/modes/track/ . Thư viện LAP cài qua requirements để tránh tải phụ thuộc tự động lúc bắt đầu tracking.
