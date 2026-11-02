# Checklist dự án — cập nhật 02/11/2026

`[x]` = có bằng chứng đã làm/đã kiểm thử như ghi bên cạnh. `[ ]` = chưa làm hoặc chưa được xác nhận; có code không đồng nghĩa đã chạy trên mạch thật.

## 1. Camera

- [x] ESP32-CAM kết nối Wi-Fi và chụp ảnh: người dùng đã xác nhận.
- [x] Python nhận ảnh `/capture` và lưu JPG: người dùng đã xác nhận lưu ảnh.
- [ ] MJPEG `:81/stream` hoạt động ổn định: lần thử trước bị timeout.
- [ ] Chạy camera 5–10 phút, mở lại và thử rút nguồn: cần người dùng kiểm tra.

## 2. Nhận diện xe

- [x] Cài YOLOv8n và đọc ảnh/video/camera snapshot.
- [x] Vẽ khung, loại xe, confidence, FPS; lưu ảnh kết quả.
- [x] Kiểm thử ảnh bus: phát hiện 1 bus khoảng 0.88 confidence.
- [ ] Đánh giá video giao thông thật của nhóm, xe mô hình và trường hợp che khuất.

## 3. Tracking và vạch dừng

- [x] ByteTrack gán ID, cấu hình vạch, xác định hai chiều và hạn chế rung/ghi lặp cùng lượt.
- [x] Thêm chọn hai đầu vạch bằng chuột, Enter xác nhận, R chọn lại (đã có code).
- [x] 11 kiểm thử logic vạch dừng đạt.
- [x] Video tổng hợp 41 frame: giữ ID 1, ghi đúng 1 crossing; video đứng yên: 0 crossing.
- [ ] Người dùng thử chọn vạch bằng chuột, lưu ảnh/thoát và đặt vạch trên cảnh thật.
- [ ] Kiểm tra nhiều xe, mất tracking và ID đổi trên video thực.

## 4. Mốc vừa làm: MQTT và ghép đèn

- [x] Thêm Python nhận state/status đúng hợp đồng firmware; lọc device và kiểm tra dữ liệu.
- [x] Hiển thị RED/YELLOW/GREEN/UNKNOWN; quá hạn 1.5 giây hoặc offline/disconnect thì UNKNOWN.
- [x] Bỏ trạng thái retained; online/reconnect cần bản tin màu mới.
- [x] Tự kết nối lại broker và đăng ký lại topic.
- [x] Ghép khoảng qua vạch với lịch sử đèn; lọc chiều, thêm khoảng dự phòng thời gian.
- [x] Ghi `assessment` vào JSONL; không đánh dấu nghi vượt đèn đỏ khi thiếu trạng thái đáng tin cậy.
- [x] 16 kiểm thử logic màu đèn/phân loại đạt.
- [x] Mosquitto 2.1.2 chạy được trên laptop; bài tích hợp MQTT thật qua loopback đạt (không dùng ESP32).
- [x] Kiểm thử tích hợp: ba màu, retained, heartbeat timeout, offline, tắt broker và kết nối lại.
- [x] Tạo simulator và hướng dẫn thử bằng ba cửa sổ PowerShell: [MQTT_PYTHON.md](docs/MQTT_PYTHON.md).
- [ ] Xác nhận ESP32 DevKit/LED, chân GPIO và chu kỳ trên mạch thật.
- [ ] Tạo tài khoản broker LAN, cấu hình kết nối/firewall và nạp sketch đèn bằng Arduino IDE.
- [ ] Python nhận đúng màu LED thật, tắt ESP32/broker thì về UNKNOWN, bật lại tự phục hồi.
- [ ] Chạy đồng thời camera + ESP32 đèn + YOLO + crossing; test đỏ/xanh/dừng trước vạch.
- [ ] Đo độ trễ camera/MQTT và kiểm thử sát thời điểm đổi màu; chưa coi đây là đồng bộ thời gian đã hoàn thành.

**Không sửa/nạp firmware trong mốc này.** Phần chưa xác nhận trên mạch được giữ trống để nhóm tự đánh dấu sau khi thử thành công.

## 5. Logic đèn đỏ — hoàn thiện phần mềm

- [x] Dùng chung hàm `assess_crossing` trong chương trình camera để phân loại và ghi lý do `assessment_reason`.
- [x] Kiểm tra đúng chiều, đỏ liên tục và khoảng dự phòng; không khẳng định khi đổi màu/thiếu dữ liệu.
- [x] Demo 14 tình huống đạt, gồm xe dừng, đã qua trước khi đỏ, qua lúc xanh rồi mới đỏ, mất heartbeat, đổi ID và chống ghi lặp cùng lượt.
- [x] Chặn timestamp NaN/vô hạn hoặc khoảng thời gian đảo ngược để không tạo kết luận đỏ sai.
- [x] Tổng 33 bài unittest đạt; hướng dẫn/demo tại [RED_LIGHT_LOGIC.md](docs/RED_LIGHT_LOGIC.md).
- [ ] Xác nhận các tình huống này trên camera + ESP32 đèn thật, kiểm tra độ trễ sát thời điểm đổi màu.

## 6. SQLite và ảnh bằng chứng

- [x] SQLite tự lưu mọi crossing với ID, thời gian, loại xe, màu đèn, kết quả/lý do và đường dẫn ảnh.
- [x] Nghi vượt đèn đỏ tự lưu ảnh gốc, ảnh có khung và ảnh cắt xe; ảnh lưu riêng, database không lưu BLOB.
- [x] Tùy chọn lưu ảnh mọi crossing để thử, không thay đổi UNKNOWN thành đỏ.
- [x] Khóa duy nhất event_id chống ghi trùng cùng sự kiện; lỗi ghi ảnh/INSERT có rollback và dọn file vừa tạo.
- [x] Thêm công cụ đọc/lọc sự kiện và demo lưu trữ không cần camera: [STORAGE.md](docs/STORAGE.md).
- [x] 9 kiểm thử storage đạt; tổng hiện tại 42 bài đạt.
- [x] Chạy toàn luồng video tổng hợp 41 frame: YOLO → ByteTrack → 1 crossing → SQLite và 3 ảnh; đã đọc lại và mở ảnh cắt xe.
- [ ] Kiểm tra tự lưu bằng chứng nghi đỏ trên camera + ESP32 đèn thật.
- [ ] Kiểm tra phục hồi sau mất điện đột ngột và sao lưu/chuyển đường dẫn trên máy thật.

## 7. Giao diện Streamlit local

- [x] Đọc SQLite chỉ đọc; chọn nguồn chạy thật/demo/video mẫu/đường dẫn khác.
- [x] Danh sách có phân trang, thống kê và biểu đồ theo kết quả lọc.
- [x] Lọc kết quả, loại xe, màu đèn, ngày; tìm ID/nguồn.
- [x] Xem ba ảnh bằng chứng và JSON chi tiết; xử lý thiếu database/ảnh hoặc bộ lọc rỗng.
- [x] Tải CSV trang hiện tại và làm mới dữ liệu theo nút bấm.
- [x] 6 kiểm thử dashboard đạt (gồm một bài tương tác Streamlit AppTest); tổng 48 bài đạt.
- [x] Chạy máy chủ local, trang chủ HTTP 200 và health endpoint OK; hướng dẫn [DASHBOARD.md](docs/DASHBOARD.md).
- [ ] Người dùng kiểm tra bố cục trong trình duyệt, thao tác tải CSV và ảnh thực tế.
- [ ] Kiểm tra cùng luồng camera/đèn thật đang ghi database trong buổi demo.

## 8. Chưa triển khai

- [ ] Phát hiện biển số và OCR.
- [ ] Demo toàn luồng, ghi kết quả và giới hạn vào báo cáo.

## Cách kiểm tra nhanh

1. Chạy `python -m unittest discover -s tests -v` bằng Python `.venv`: hiện tại 48 bài đạt. Xem rõ SKIP/FAIL nếu có trên máy khác.
2. Thử MQTT không cần mạch theo mục ba cửa sổ trong [hướng dẫn](docs/MQTT_PYTHON.md).
3. Chỉ đánh dấu các ô phần cứng khi đã thấy kết quả đúng trên mạch và log thực tế.
4. Xem logic đèn đỏ không cần phần cứng: `.\.venv\Scripts\python.exe python/red_light_demo.py`.
5. Thử lưu SQLite và ảnh không cần phần cứng: `.\.venv\Scripts\python.exe python/storage_demo.py`.
6. Mở giao diện theo [DASHBOARD.md](docs/DASHBOARD.md), chọn Demo lưu trữ để xem ngay.
