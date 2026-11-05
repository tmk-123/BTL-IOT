# Định hướng và tiến độ dự án

**Mô phỏng không đèn 03/11:** đã thêm bảng đèn Xanh/Đỏ/Vàng/Ngừng gửi qua MQTT thật, chọn vạch trên camera có cập nhật trực tiếp, lưu sự kiện/ảnh có nhãn mô phỏng riêng và nguồn xem trong dashboard. Ba bài pipeline HTTP/video fixture kiểm tra xanh/đỏ/UNKNOWN đạt; camera vật lý trả ảnh nhưng kết nối chưa ổn định, chờ người dùng căn vào video và chọn vạch. Hướng dẫn: [MO_PHONG_KHONG_DEN.md](MO_PHONG_KHONG_DEN.md).

**Bổ sung 03/11/2026:** đã tải detector biển số YOLOv9-t và OCR CCT-XS ONNX, thêm `python/plate_scanner.py` cho ESP32-CAM `/capture`/stream, webcam và ảnh. Đã chạy CPU trên ảnh mẫu, lưu JPG/JSON và đọc được `5AU5341`; chưa kiểm thử biển Việt Nam/camera thật, chưa ghép OCR vào SQLite/Streamlit. Xem [BIEN_SO.md](BIEN_SO.md).

**Kiểm thử tiếp 03/11:** đã chạy thêm 4 ảnh Việt Nam có sẵn, phát hiện 10 vùng biển (có biển xe máy hai dòng), đối chiếu trực quan OCR khớp ở các vùng tìm thấy; cảnh đông xe còn bỏ sót biển nhỏ. Đây là thử nhanh, chưa phải benchmark hoặc kiểm thử camera thật. Kết quả và lệnh chạy lại trong BIEN_SO.md.

**Video 03/11:** thêm `--video`, xuất MP4/JSONL/summary và chạy đủ 835 frame của video giao thông Việt Nam có sẵn. 477 frame có biển được phát hiện, khoảng 6.27 FPS CPU; OCR còn dao động/sai khi biển mờ. Chưa ghép tracking OCR/sự kiện hoặc xác nhận thời gian thực. Xem bước 3 trong BIEN_SO.md.

**Ổn định OCR 03/11:** đã thêm theo dõi vùng biển riêng và bỏ phiếu theo cửa sổ, PENDING khi thiếu bằng chứng, log raw/stable. Chạy lại 835 frame có 5 chuỗi đồng thuận khớp ảnh cắt, 9 kiểm thử ALPR đạt và snapshot/Tk local đạt. Chưa ghép ID xe ByteTrack/sự kiện/SQLite. Xem bước 4 trong BIEN_SO.md.

**Tích hợp sự kiện 03/11:** đã ghép biển với ID xe ByteTrack bằng `--plate-ocr`, lưu biển/trạng thái/ảnh vào SQLite và xem/tìm trong Streamlit. Chạy 150 frame đầu video mẫu: 3 crossing UNKNOWN/unverified, trong đó ID 1 có biển `29A33185`, hai sự kiện còn lại chưa có biển ổn định. 66 kiểm thử đạt; preset **Video biển số** có dữ liệu để xem. Camera + đèn thật vẫn chờ kiểm thử. Xem bước 5 trong BIEN_SO.md.

Cập nhật: **02/11/2026**. Đọc file này để biết đang làm đến đâu; xem [DECISIONS.md](DECISIONS.md) để biết lựa chọn kỹ thuật và lý do.

Ghi nhận mới 02/11: người dùng đã xem/lưu ảnh qua `/capture`. MJPEG `:81/stream` vẫn timeout, chưa hoàn tất kiểm thử stream 5–10 phút và mất kết nối. Đã thêm YOLOv8n và ByteTrack/vạch dừng; hướng dẫn tại [YOLO.md](YOLO.md) và [TRACKING.md](TRACKING.md). Đã thêm nhận/ghép trạng thái đèn theo [MQTT_PYTHON.md](MQTT_PYTHON.md), SQLite và ảnh theo [STORAGE.md](STORAGE.md). Kiểm thử phần mềm/broker local/video tổng hợp đạt, chờ thử chung trên mạch thật. OCR và ứng dụng chưa triển khai. Theo dõi bằng [CHECKLIST.md](../CHECKLIST.md).

## 1. Mục tiêu bàn giao

Cập nhật bổ sung trong ngày: giao diện Streamlit local đã có bộ lọc, thống kê và xem ảnh SQLite theo [DASHBOARD.md](DASHBOARD.md), 6 tests dashboard đạt (tổng 48). Phần ứng dụng xem dữ liệu đã triển khai bản thử; OCR vẫn chưa triển khai. Chưa xác nhận demo toàn luồng trên phần cứng thật.

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
| Lưu dữ liệu | SQLite, ảnh nằm trong thư mục riêng | Đã có bản chạy thử và 9 kiểm thử storage; xem STORAGE.md |
| Giao diện | Streamlit local | Đã có bản thử, AppTest đạt; chờ kiểm tra trình duyệt và buổi demo thực tế |
| Biển số và OCR        | Chưa chốt công cụ/model              | Thử trên ảnh thật trước khi chọn                               |

Chi tiết, phương án thay thế và điều kiện xem xét lại nằm trong [nhật ký quyết định](DECISIONS.md).

## 3. Tiến độ thực tế

| Phần việc                                         | Trạng thái                                 | Bằng chứng/việc còn thiếu                                     |
| --------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------ |
| Camera và Wi-Fi                                    | Đã test theo xác nhận của người dùng | Người dùng xác nhận testCamera xong                           |
| Sắp xếp mã nguồn                                | Đã làm                                    | Sketch nằm trong firmware, ảnh phần cứng trong docs/hardware   |
| Python nhận hình, FPS, S lưu ảnh, Q thoát      | Đã có code                                | Đã kiểm tra lưu JPG/thoát/lỗi mở kết nối bằng mô phỏng |
| Camera thật vào Python | Đã lưu ảnh qua /capture | Người dùng xác nhận; MJPEG /stream vẫn timeout, chưa kiểm tra đầy đủ mất kết nối/chạy dài |
| LED và MQTT                                        | Đã có firmware/cấu hình                 | Chưa có xác nhận chạy thành công trên mạch thật          |
| Nhận diện xe YOLOv8n | Đã có bản thử | Nhận 1 bus trên ảnh mẫu; đọc hết video thử 5 frame; camera /capture suy luận 3 frame; xem YOLO.md |
| ByteTrack và vạch dừng | Đã có bản thử | 11 unit tests đạt; video tổng hợp 41 frame giữ ID 1 và sinh 1 crossing; chưa đánh giá video thực |
| Nhận/ghép trạng thái đèn MQTT | Đã có bản thử | 16 unit tests và 1 bài tích hợp Mosquitto thật đạt; chưa xác nhận chung với camera/LED thật |
| SQLite và ảnh bằng chứng | Đã có bản thử | 9 tests storage đạt; lưu/đọc 1 crossing và 3 ảnh từ video tổng hợp; chờ thử camera/đèn thật |
| Giao diện Streamlit | Đã có bản thử | 6 tests dashboard đạt; localhost HTTP 200/health OK |
| OCR | Đã có công cụ thử riêng ngày 03/11 | Model ONNX chạy ảnh mẫu thành công; cần camera/biển Việt Nam và tích hợp sự kiện |

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
