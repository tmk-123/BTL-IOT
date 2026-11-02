# Nhật ký quyết định kỹ thuật

Cập nhật: **01/11/2026**. File tổng hợp lựa chọn đã xác nhận và đề xuất còn mở; xem [định hướng dự án](DINH_HUONG_DU_AN.md) để theo dõi tiến độ.

Trạng thái: **BẮT BUỘC**, **ĐÃ CHỐT**, **ĐÃ THỐNG NHẤT HƯỚNG**, **ĐỀ XUẤT/CHƯA CHỐT**. Chốt hướng công nghệ không đồng nghĩa đã chọn phiên bản cụ thể hay đã kiểm thử thành công.

## D-00 — Arduino IDE: BẮT BUỘC

- Ghi nhận từ tài liệu dự án trước đây, giữ nguyên ngày 12/10/2026.
- Dùng Arduino IDE để viết, biên dịch và nạp firmware ESP32.
- Không chuyển công cụ nạp sang PlatformIO khi chưa có yêu cầu thay đổi từ người dùng.

## D-01 — MQTT cho trạng thái đèn: ĐÃ CHỐT

- Lịch sử: nhật ký Git ghi chốt ngày 12/10/2026; người dùng xác nhận lại ngày 01/11/2026.
- Cân nhắc: HTTP polling, HTTP đẩy trạng thái, MQTT.
- Quyết định: ESP32 điều khiển đèn publish MQTT; Mosquitto trên laptop; Python subscribe.
- Lý do: phù hợp môn IoT, gửi ngay khi đổi đèn, có heartbeat và Last Will hỗ trợ phát hiện mất kết nối.
- Đánh đổi: cần broker, tài khoản và cấu hình mạng LAN; firmware hiện publish QoS 0.
- Cấu hình hiện có: `traffic/inter1/light/state` cho JSON, `traffic/inter1/light/status` cho online/offline. Hợp đồng payload: [firmware README](../firmware/esp32_traffic_light/README.md).
- Điều kiện xem xét lại: mạng demo không cho thiết bị kết nối hoặc không chạy được broker. HTTP chỉ là phương án dự phòng cần thống nhất lại, không tự thay MQTT.

## D-02 — Camera HTTP và OpenCV: ĐÃ CHỐT CHO BƯỚC HIỆN TẠI

- Ngày: 01/11/2026, theo yêu cầu triển khai Camera → Python của người dùng.
- ESP32-CAM phát MJPEG qua HTTP/Wi-Fi tại `http://<IP>:81/stream`; Python/OpenCV trên laptop nhận hình, hiển thị và lưu JPG.
- MQTT chỉ mang trạng thái đèn trong kiến trúc hiện tại.
- Lý do: dùng tiếp firmware camera đã test, nối trực tiếp với phần xử lý ảnh trên laptop.
- Đánh đổi: chất lượng và tốc độ phụ thuộc nguồn camera, Wi-Fi, độ phân giải; cần kiểm thử thật.
- Xem xét lại cấu hình khi hình giật, trễ hoặc không đủ rõ để nhận dạng.

## D-03 — YOLO bản nhỏ và ByteTrack: ĐÃ THỐNG NHẤT HƯỚNG

- Ngày: 01/11/2026; người dùng đồng ý đề xuất trong cuộc trao đổi hiện tại.
- Cân nhắc: model phát hiện xe phù hợp và tracking ByteTrack/SORT.
- Hướng triển khai: thử YOLO bản nhỏ + ByteTrack trên hình camera thật.
- Lý do: phù hợp luồng phát hiện xe rồi theo dõi ID qua nhiều frame; bắt đầu với model nhỏ để đánh giá tốc độ laptop.
- Chưa chốt: phiên bản YOLO, trọng số, ngưỡng confidence và tốc độ/độ chính xác chấp nhận được.
- Trước khi chọn model: kiểm tra tương thích môi trường, giấy phép mã nguồn/trọng số/dataset và kết quả thực tế. Thay model khi chất lượng hoặc tốc độ không đạt.

## D-04 — SQLite và ảnh riêng: ĐÃ THỐNG NHẤT HƯỚNG

- Ngày: 01/11/2026; người dùng đồng ý đề xuất.
- Cân nhắc: SQLite hoặc MySQL.
- Chọn SQLite cho bản local; ảnh lưu trong thư mục, database lưu đường dẫn cùng thông tin sự kiện.
- Lý do: triển khai đơn giản trên laptop, không cần server database riêng.
- Đánh đổi: cần quản lý nhất quán file ảnh và bản ghi; đánh giá lại khi có nhiều máy cùng ghi hoặc yêu cầu MySQL từ môn học.

## D-05 — Streamlit local: ĐÃ THỐNG NHẤT HƯỚNG

- Ngày: 01/11/2026; người dùng đồng ý đề xuất.
- Cân nhắc: Streamlit hoặc Flask/FastAPI cùng frontend.
- Chọn Streamlit cho bản đầu: danh sách sự kiện, ảnh, bộ lọc và thống kê.
- Lý do: ưu tiên hoàn thành giao diện tra cứu local bằng Python.
- Đánh đổi: mức tùy biến giao diện và API; đánh giá lại nếu có yêu cầu mobile/API/giao diện vượt khả năng bản đầu.

## D-06 — Biển số và OCR: CHƯA CHỐT

- Cập nhật: 01/11/2026.
- Cần thử model phát hiện biển số và OCR trên ảnh thật, gồm biển số xe máy hai dòng nếu thuộc phạm vi demo.
- Phương án khảo sát: EasyOCR, PaddleOCR hoặc Tesseract; chưa cài/chọn mặc định một công cụ.
- Đề xuất: so sánh khả năng đọc, tốc độ, tương thích và giấy phép trước khi chốt.
- Giữ ảnh, kết quả thô và độ tin cậy khi có; không đọc được biển số vẫn giữ sự kiện để kiểm tra.

## D-07 — Đồng bộ thời gian: ĐỀ XUẤT

- Kế thừa hướng đề xuất cũ; cập nhật 01/11/2026, chưa có xác nhận chốt.
- Dùng đồng hồ laptop, suy ra thời điểm chuyển đèn từ thời điểm nhận và `ms_in_state`; cần đánh giá sai số truyền hình/mạng trước khi kết luận vượt đèn.
- Heartbeat firmware hiện là 1 giây. Ngưỡng hết hạn 1,5 giây là đề xuất cần kiểm thử và cấu hình được.
- Mất kết nối, offline hoặc trạng thái hết hạn: UNKNOWN. Nguyên tắc này giữ theo yêu cầu độ tin cậy của dự án.
- Đánh giá lại nếu cần NTP/RTC hoặc đồng bộ log từ nhiều thiết bị.

## D-08 — Môi trường local: HIỆN ĐÃ TRIỂN KHAI

- Cập nhật: 01/11/2026.
- Python 3.13 trên máy hiện tại, `.venv` và `requirements.txt`; OpenCV đã cài cho bước nhận hình.
- Đây là môi trường đã dùng, chưa phải cam kết mọi thư viện AI/OCR đều tương thích.
- Đề xuất tiếp tục local, chưa thêm Docker/cloud. Đổi phiên bản Python khi kiểm tra thư viện sau này cho thấy cần thiết.

## D-09 — GPIO và bố trí board: CHƯA XÁC NHẬN MẠCH THẬT

- Cập nhật: 01/11/2026.
- Firmware đèn hiện dùng GPIO đỏ 25, vàng 26, xanh 27, active-HIGH; chu kỳ xanh 10 giây, vàng 3 giây, đỏ 10 giây.
- Đây là cấu hình mẫu cho ESP32 DevKit, chưa được người dùng xác nhận đấu dây và kiểm thử.
- Camera và đèn có sketch riêng. Trước khi ghép phải xác nhận board, nguồn, chân thực tế; không dùng GPIO mẫu của DevKit cho ESP32-CAM khi chưa kiểm tra xung đột.

## Cách sửa nhật ký

Ghi ngày, vấn đề, phương án cân nhắc, kết luận, lý do, đánh đổi và điều kiện xem xét lại. Đánh dấu rõ nội dung người dùng đã xác nhận; giữ phần chưa quyết định ở trạng thái đề xuất.
