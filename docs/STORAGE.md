# Lưu sự kiện và ảnh bằng chứng

Mốc này dùng SQLite có sẵn trong Python, không cần cài thêm database server. Không sửa firmware.

## Thử ngay không cần camera

```powershell
.\.venv\Scripts\python.exe python/storage_demo.py
.\.venv\Scripts\python.exe python/list_events.py --database data/demos/storage/traffic.db --limit 1
```

Demo tạo hình xe giả lập, dùng kết quả logic đỏ để lưu một sự kiện và ba JPEG. Chương trình gửi lại cùng ID để kiểm tra chống trùng; chỉ có một bản ghi cho ID đó. Mỗi lần chạy demo mới tạo phiên mới nên thêm một sự kiện mới. Dữ liệu demo tách khỏi database chạy thật và có `simulation: true`; đây không phải bằng chứng vi phạm thật hoặc kiểm thử nhận diện xe.

Mở ảnh theo đường dẫn terminal in ra:

- `original.jpg`: ảnh đầu vào, chưa vẽ khung/nhãn của chương trình nhận diện.
- `annotated.jpg`: ảnh có khung, ID, vạch và kết quả phân loại.
- `vehicle.jpg`: ảnh cắt từ ảnh gốc theo bbox, giới hạn trong kích thước frame.

## Khi chạy chương trình nhận diện

Chạy camera/YOLO/tracking như trước. Khi có `--track` hoặc `--select-line`, chương trình tự mở SQLite và lưu mọi crossing, kể cả xanh/vàng/UNKNOWN. Mặc định **chỉ `suspected_red_light` tự lưu ảnh**, các sự kiện khác có đường dẫn ảnh NULL.

```text
data/traffic.db                       SQLite chạy thật
data/evidence/<hash-id>/original.jpg
data/evidence/<hash-id>/annotated.jpg
data/evidence/<hash-id>/vehicle.jpg
data/detections/crossings_*.jsonl      Log phụ, có thêm đường dẫn ảnh
```

Kiểm tra toàn luồng bằng video mẫu đã có trên máy, chưa cần MQTT:

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source data/samples/bus_moving.avi --track --line 0.1 0.65 0.9 0.65 --save-all-evidence --database data/demos/storage_pipeline/traffic.db --evidence-dir data/demos/storage_pipeline/evidence --output data/demos/storage_pipeline/logs
.\.venv\Scripts\python.exe python/list_events.py --database data/demos/storage_pipeline/traffic.db --limit 1
```

`--save-all-evidence` lưu ảnh cho cả crossing không có bằng chứng đỏ để kiểm tra. Nó **không đổi kết quả phân loại**: video mẫu không có nguồn đèn vẫn là UNKNOWN/unverified. Bỏ tùy chọn này khi chỉ muốn ảnh nghi vượt đèn đỏ.

Đổi chỗ lưu bằng `--database` và `--evidence-dir`. `--output` chỉ đổi nơi lưu JSONL/ảnh nhấn S, không đổi database và thư mục bằng chứng. Nếu không bật tracking, không tự tạo database.

## Xem dữ liệu thật

```powershell
.\.venv\Scripts\python.exe python/list_events.py --limit 10
.\.venv\Scripts\python.exe python/list_events.py --assessment suspected_red_light --limit 10
```

Công cụ chỉ đọc, không tạo database trống khi sai đường dẫn. Đã bổ sung giao diện xem bằng Streamlit tại [DASHBOARD.md](DASHBOARD.md). Bản ghi gồm thời gian laptop, nguồn, phiên chạy, frame, ID xe, loại xe/confidence, hướng, bbox, vạch, màu đèn, kết quả/lý do và đường dẫn ảnh. OCR chưa triển khai nên chưa có kết quả biển số.

## Tính nhất quán và giới hạn

- `event_id` là khóa duy nhất; ghi lại cùng ID trả về bản ghi cũ, không tạo ảnh mới. Hai lần chạy video là hai phiên khác nhau, không tự khử trùng giữa phiên hoặc giữa các ID tracking bị đổi.
- Tên thư mục ảnh là hash ID, không dùng ID trực tiếp làm đường dẫn. Database dùng tham số SQL.
- Ghi đủ ảnh trong thư mục tạm, đổi tên thư mục, rồi commit SQLite. Lỗi ghi ảnh/INSERT trong lúc chạy sẽ rollback và dọn đúng những file vừa tạo; chương trình nhận diện báo lỗi và dừng thay vì âm thầm bỏ dữ liệu.
- SQLite là dữ liệu chính; JSONL là log phụ, không có transaction chung với SQLite. Nếu ghi JSONL lỗi sau commit, bản ghi SQLite vẫn còn.
- Filesystem và SQLite không có transaction chung khi mất điện/kill tiến trình. Có thể còn thư mục tạm/ảnh không có bản ghi nếu chết đúng giữa bước ghi ảnh và commit. Không tự xóa ảnh cũ; cần kiểm tra/khôi phục thủ công trước khi thử lại ID đó.
- Đường dẫn ảnh hiện lưu tuyệt đối. Khi sao lưu cần giữ cả database và thư mục ảnh; chuyển sang máy/đường dẫn khác cần điều chỉnh đường dẫn. Chưa làm công cụ backup, retention hay di chuyển.
- `data/` đã được Git bỏ qua. Sự kiện hiện chỉ là nghi vi phạm để kiểm tra lại, chưa phải kết luận xử phạt.

## Đã kiểm thử 02/11/2026

Tổng 42 bài đạt, gồm 9 bài storage: lưu/đọc lại, đường dẫn tiếng Việt, cắt ảnh, metadata không ảnh, lưu mọi crossing, chống trùng, lỗi ghi ảnh và rollback khi INSERT lỗi. Đã chạy video bus tổng hợp 41 frame qua YOLO/ByteTrack và lưu một sự kiện UNKNOWN cùng ba ảnh bằng tùy chọn thử. Chưa kiểm tra trường hợp đỏ từ camera + ESP32 đèn thật, mất điện đột ngột hoặc hết dung lượng ổ đĩa thật; lỗi ghi ảnh được mô phỏng trong kiểm thử.
