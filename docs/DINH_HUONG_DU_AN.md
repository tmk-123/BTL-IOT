# Định hướng và tiến độ dự án

Cập nhật: **01/11/2026**. Đọc file này để biết đang làm đến đâu; xem [DECISIONS.md](DECISIONS.md) để biết lựa chọn kỹ thuật và lý do.

## 1. Mục tiêu bàn giao

Xây dựng mô hình phát hiện xe đi qua vạch dừng khi đèn đỏ, lưu ảnh bằng chứng và kết quả nhận dạng biển số để tra cứu trên ứng dụng local.

Luồng sản phẩm:

```text
ESP32-CAM -- video qua HTTP/Wi-Fi --> Python/OpenCV trên laptop
                                             |
ESP32 điều khiển LED -- MQTT/Mosquitto --------+ trạng thái đèn
                                             |
                                   Nhận diện xe + tracking
                                             |
                              Xe vượt vạch + đèn đỏ đáng tin cậy
                                             |
                                  Ảnh bằng chứng + biển số/OCR
                                             |
                                   SQLite + thư mục ảnh
                                             |
                                     Streamlit local
```

HTTP phục vụ video; MQTT phục vụ trạng thái đèn. MQTT đã chốt không có nghĩa là chuyển video sang MQTT.
Firmware hiện tách sketch camera và sketch đèn. Việc đấu mạch thực tế cần được xác nhận trước khi tích hợp; không áp dụng mặc định GPIO của DevKit lên ESP32-CAM.

## 2. Các hướng đã thống nhất

| Hạng mục               | Lựa chọn                               | Phạm vi đã chốt                                                   |
| ------------------------ | ---------------------------------------- | --------------------------------------------------------------------- |
| Lập trình/nạp ESP32   | Arduino IDE                              | Yêu cầu bắt buộc                                                  |
| Xử lý trên laptop     | Python + OpenCV                          | Đã triển khai bước nhận hình                                   |
| Nguồn hình hiện tại  | ESP32-CAM, stream HTTP qua Wi-Fi         | Camera đã test; đang kiểm tra đường truyền vào Python        |
| Trạng thái đèn       | MQTT, Mosquitto trên laptop             | Đã chốt giao thức; chưa xác nhận test phần cứng thành công |
| Nhận diện và tracking | YOLO bản nhỏ + ByteTrack               | Thống nhất hướng; chưa chọn phiên bản/model cụ thể          |
| Lưu dữ liệu           | SQLite, ảnh nằm trong thư mục riêng | Thống nhất cho bản local; chưa triển khai                        |
| Giao diện               | Streamlit local                          | Thống nhất cho bản đầu; chưa triển khai                        |
| Biển số và OCR        | Chưa chốt công cụ/model              | Thử trên ảnh thật trước khi chọn                               |

Chi tiết, phương án thay thế và điều kiện xem xét lại nằm trong [nhật ký quyết định](DECISIONS.md).

## 3. Tiến độ thực tế

| Phần việc                                         | Trạng thái                                 | Bằng chứng/việc còn thiếu                                     |
| --------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------ |
| Camera và Wi-Fi                                    | Đã test theo xác nhận của người dùng | Người dùng xác nhận testCamera xong                           |
| Sắp xếp mã nguồn                                | Đã làm                                    | Sketch nằm trong firmware, ảnh phần cứng trong docs/hardware   |
| Python nhận hình, FPS, S lưu ảnh, Q thoát      | Đã có code                                | Đã kiểm tra lưu JPG/thoát/lỗi mở kết nối bằng mô phỏng |
| Stream camera thật vào Python                     | Chờ kiểm thử                              | Cần IP camera và chạy thử trên cùng Wi-Fi                    |
| LED và MQTT                                        | Đã có firmware/cấu hình                 | Chưa có xác nhận chạy thành công trên mạch thật          |
| AI, tracking, vượt vạch, OCR, SQLite, ứng dụng | Chưa triển khai                            | Là các mốc tiếp theo                                           |

“Có code” không đồng nghĩa “đã chạy thành công trên phần cứng”. Chỉ cập nhật hoàn thành sau khi có kết quả kiểm thử thực tế.

## 4. Việc hiện tại: hoàn tất Camera → Python

1. Bật camera với firmware testCamera đã nạp; lấy IP từ Serial Monitor 115200.
2. Chạy `python/camera_viewer.py` bằng Python trong `.venv`, truyền URL `http://<IP>:81/stream`.
3. Click cửa sổ video, nhấn S và mở ảnh trong `data/snapshots/`.
4. Chạy 5–10 phút, kiểm tra hình cập nhật; nhấn Q, chạy lại.
5. Thử mất nguồn camera để kiểm tra báo lỗi khi mất stream.
6. Ghi nhận FPS, độ rõ, độ phân giải và hiện tượng giật/đứng nếu có.

**Tiêu chí xong:** laptop nhận hình liên tục, lưu ảnh đúng, thoát và mở lại được. Hướng dẫn lệnh chi tiết: [CAMERA_PYTHON.md](CAMERA_PYTHON.md).

Firmware đang khởi động QVGA 320×240. Đây là cấu hình kiểm tra truyền hình; cần đánh giá lại góc quay, ánh sáng và độ phân giải trước khi làm nhận dạng biển số.

## 5. Lộ trình tiếp theo

| Thứ tự | Mốc                         | Điều kiện hoàn thành                                                                                                       |
| -------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 1        | Camera → Python             | Xem và lưu ảnh thật thành công theo checklist trên                                                                       |
| 2        | Nhận diện xe               | Thử YOLO bản nhỏ trên ảnh/video thật, hiển thị khung và loại xe; đo tốc độ, ghi lỗi nhận diện                  |
| 3        | Tracking và vạch dừng     | Có ID xe, hướng qua vạch, mỗi lượt qua chỉ sinh một sự kiện; xe dừng trước vạch không sinh sự kiện            |
| 4        | Đèn và MQTT               | LED đúng chu kỳ, Python nhận trạng thái/đổi đèn; mất kết nối hoặc dữ liệu hết hạn chuyển UNKNOWN             |
| 5        | Ghép sự kiện vượt đèn | Chỉ ghi nghi vi phạm khi xe qua vạch trong trạng thái đỏ đáng tin cậy; test xanh/đỏ/dừng/mất mạng                |
| 6        | Bằng chứng và SQLite      | Lưu thời gian, ID xe, trạng thái đèn, ảnh và đường dẫn; tránh bản ghi trùng                                      |
| 7        | Biển số/OCR                | Thử model/công cụ trên ảnh thật, lưu kết quả và độ tin cậy; vẫn giữ sự kiện khi không đọc được biển số |
| 8        | Streamlit                    | Xem danh sách, ảnh, lọc theo thời gian/biển số, thống kê cơ bản                                                       |
| 9        | Kiểm thử và báo cáo     | Demo toàn luồng, kiểm tra mất mạng/che khuất/ảnh mờ, ghi giới hạn và kết quả                                       |

Có thể kiểm tra mạch LED/MQTT sớm nếu phần cứng sẵn sàng. Hoàn thành từng mốc nhỏ trước khi mở rộng cloud, mobile hoặc nhiều camera.

## 6. Quy tắc cập nhật

- Đổi lựa chọn kỹ thuật: cập nhật DECISIONS.md trước, nêu lý do và phạm vi ảnh hưởng.
- Chốt mới với người dùng rồi mới ghi “đã chốt”; đề xuất phải giữ nhãn đề xuất.
- Sau mỗi mốc: cập nhật trạng thái, ngày kiểm thử và kết quả thật tại đây.
- Model/version, GPIO thực tế, cách đồng bộ thời gian và OCR còn cần đánh giá; không tự coi cấu hình mẫu là quyết định cuối.
- Không kết luận vi phạm từ một ảnh đơn lẻ; phải có sự kiện qua vạch và trạng thái đèn đáng tin cậy. Khi không rõ trạng thái đèn dùng UNKNOWN.
