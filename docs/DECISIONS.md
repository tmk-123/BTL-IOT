# DECISIONS — Nhật ký quyết định kỹ thuật

Mỗi quyết định có trạng thái:

- **BẮT BUỘC** — yêu cầu của đề tài, không thay đổi.
- **ĐỀ XUẤT** — chờ nhóm xác nhận.
- **ĐÃ CHỐT** — nhóm đã xác nhận; muốn đổi phải ghi mục mới.

---

## D-00. Công cụ firmware ESP32 — BẮT BUỘC

- Ngày: 2026-10-12
- Quyết định: dùng **Arduino IDE** để viết, biên dịch và nạp firmware ESP32. Không dùng PlatformIO.
- Ghi chú: file đặc tả `.docx` (mục 10) đang ghi "Arduino IDE hoặc PlatformIO" — mâu thuẫn, cần sửa đặc tả theo yêu cầu này.

---

## D-01. Giao tiếp ESP32 – laptop — ĐÃ CHỐT: MQTT

- Ngày: 2026-10-12 (đề xuất HTTP ban đầu; chốt MQTT cùng ngày sau khi người dùng xác nhận)
- Phương án đã cân nhắc:
  1. HTTP, laptop hỏi ESP32 (polling) `GET /state` ~200 ms/lần.
  2. HTTP, ESP32 đẩy lên laptop (`POST` mỗi khi đổi đèn + heartbeat).
  3. **MQTT**: ESP32 publish lên broker Mosquitto chạy trên laptop, Python subscribe.
- Quyết định: **phương án 3 — MQTT**.
- Lý do:
  - Môn IoT có dạy MQTT; đây là giao thức IoT tiêu chuẩn.
  - **Last Will** giải quyết sẵn yêu cầu "mất kết nối ESP32 → `UNKNOWN`"; ESP32 đẩy tin ngay khi đổi đèn (không trễ như polling); thêm bên nhận (dashboard) không phải sửa firmware.
  - Chi phí thêm nhỏ: máy đã cài sẵn Mosquitto 2.1.2 và `paho-mqtt` 2.1.0; người dùng có quyền admin để mở firewall.
- Đánh đổi: phải chạy broker, mở cổng 1883 trên Windows Firewall, quản lý tài khoản MQTT; PubSubClient chỉ publish QoS 0.
- Chi tiết triển khai:
  - Thư viện ESP32: **PubSubClient 2.8** (MIT). Broker: **Mosquitto** (EPL-2.0/EDL-1.0), cấu hình tại `tools/mosquitto/mosquitto.conf`, bắt buộc đăng nhập (`allow_anonymous false`).
  - Topic `traffic/inter1/light/state` (JSON, không retained, gửi khi đổi đèn + heartbeat 1 s) và `traffic/inter1/light/status` (`online`/`offline`, retained, `offline` là Last Will).
  - Hợp đồng payload chi tiết: `firmware/esp32_traffic_light/README.md` mục 2.
- Điều kiện thay đổi: mạng demo chặn kết nối giữa thiết bị hoặc không chạy được broker → quay về HTTP polling (chỉ thay module nhận trạng thái phía Python và phần mạng của firmware; payload JSON giữ nguyên).

## D-02. Nguồn thời gian chuẩn — ĐỀ XUẤT

- Ngày: 2026-10-12
- Đề xuất: **đồng hồ laptop là chuẩn duy nhất**. ESP32 không cần NTP/RTC. Thời điểm đổi đèn = thời điểm laptop nhận bản tin − `ms_in_state`.
- Trạng thái quá **1,5 s** (cấu hình được) không nhận bản tin `state` mới, hoặc `status` = `offline` → `UNKNOWN`. (ESP32 gửi heartbeat mỗi 1 s.)
- Timestamp lưu dạng ISO 8601 có múi giờ (ví dụ `2026-10-12T19:05:03.120+07:00`).
- Điều kiện thay đổi: nếu ESP32 và laptop cần ghi log độc lập rồi ghép sau → thêm NTP trên ESP32.

## D-03. Video có sẵn và trạng thái đèn thật — ĐỀ XUẤT

- Vấn đề: video quay sẵn có đèn giao thông riêng của nó, không khớp với chu kỳ LED trên ESP32.
- Đề xuất: hai chế độ chạy:
  - **Chế độ demo (live)**: phát video theo tốc độ thật; LED trên ESP32 được coi là đèn của nút giao trong video. Thời gian frame = đồng hồ laptop lúc đọc frame.
  - **Chế độ kiểm thử (replay)**: không dùng ESP32; đọc trạng thái đèn từ file kịch bản (ví dụ `0–10 s GREEN, 10–13 s YELLOW, 13–30 s RED`) để test lặp lại được, cho kết quả giống nhau mỗi lần chạy.
- Đánh đổi: ở chế độ demo, "vi phạm" là vi phạm so với LED của mô hình, không phải so với đèn thật trong video. Cần nói rõ khi báo cáo.

## D-04. Cơ sở dữ liệu — ĐỀ XUẤT

- Phương án: SQLite / MySQL.
- Đề xuất: **SQLite** (có sẵn trong Python, một file, không cài server). Ảnh lưu trong `data/evidence/`, DB chỉ lưu đường dẫn tương đối.
- Điều kiện thay đổi: cần nhiều máy cùng ghi đồng thời hoặc môn học yêu cầu MySQL.

## D-05. Ứng dụng xem dữ liệu — ĐỀ XUẤT

- Phương án: Streamlit / Flask hoặc FastAPI + HTML/JS.
- Đề xuất: **Streamlit** (đã có sẵn trong môi trường: streamlit 1.65.0). Ít code, có sẵn bảng, bộ lọc, biểu đồ và hiển thị ảnh.
- Đánh đổi: khó tùy biến giao diện, không hợp làm API cho app mobile.
- Điều kiện thay đổi: cần đăng nhập, API cho mobile hoặc giao diện tùy biến → Flask/FastAPI.

## D-06. Phát hiện xe và tracking — ĐỀ XUẤT

- Đề xuất: **Ultralytics YOLO bản nano (YOLOv8n hoặc YOLO11n) pretrained COCO** (lớp car, motorcycle, bus, truck) + **ByteTrack có sẵn trong Ultralytics** (`model.track(...)`).
- Giấy phép: Ultralytics là **AGPL-3.0** — dùng cho học tập thì được, nhưng nếu công khai repo hoặc dịch vụ thì phải công khai mã nguồn theo AGPL. ByteTrack: MIT. SORT gốc: GPL-3.0.
- Điều kiện thay đổi: cần giấy phép thoáng hơn → cân nhắc model khác (ví dụ YOLOX, Apache-2.0) và kiểm tra lại.

## D-07. Biển số và OCR — ĐỀ XUẤT (chưa chốt model)

- Phát hiện biển số: cần model được huấn luyện cho **biển số Việt Nam** (có biển 2 dòng của xe máy). Phải kiểm tra giấy phép model/dataset trước khi dùng, kể cả repo tham khảo trong đặc tả.
- OCR: thử **EasyOCR** trước (Apache-2.0, cài bằng pip); so sánh với PaddleOCR (Apache-2.0) trên chính ảnh của nhóm.
- Lưu cả chuỗi OCR thô, chuỗi đã chuẩn hóa và confidence; không coi OCR là chính xác tuyệt đối.

## D-08. Docker — ĐỀ XUẤT: không dùng

- Lý do: chạy local trên Windows, cần truy cập webcam và mạng LAN tới ESP32 — Docker trên Windows làm việc này phức tạp hơn. Dùng `venv` + `requirements.txt`.
- Điều kiện thay đổi: triển khai lên server/cloud.

## D-09. Phiên bản Python — ĐỀ XUẤT

- Máy hiện có Python 3.13.9. Thử cài thư viện trên 3.13 trước; nếu thư viện nào (đặc biệt PaddleOCR) chưa hỗ trợ thì tạo venv Python 3.11/3.12. Cả nhóm dùng cùng phiên bản.

## D-10. Chân GPIO cho LED — ĐỀ XUẤT (giả định khi viết bước 1a)

- Ngày: 2026-10-12
- Đề xuất: Đỏ = GPIO 25, Vàng = GPIO 26, Xanh = GPIO 27; LED nối kiểu active-HIGH qua điện trở 220 Ω.
- Lý do: là chân output thông thường, không phải chân strapping (0, 2, 5, 12, 15), không phải chân chỉ-đọc (34–39) hay chân flash (6–11).
- Hệ quả: đổi chân chỉ cần sửa `firmware/esp32_traffic_light/config.h` và `diagram.json`.
- Điều kiện thay đổi: board thực tế khác DevKit WROOM-32 hoặc nhóm đã đấu mạch theo chân khác.
