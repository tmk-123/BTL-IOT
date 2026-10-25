i 

# IoT Giao thông thông minh — Nhận dạng xe vượt đèn đỏ

## 1. Giới thiệu

Đề tài xây dựng mô hình IoT kết hợp AI để hỗ trợ phát hiện phương tiện đi qua vạch dừng khi đèn đỏ, nhận dạng biển số xe và lưu thông tin/bằng chứng để tra cứu trên ứng dụng.

Đây là mô hình học tập và hỗ trợ giám sát, **không phải hệ thống tự động xử phạt ngoài thực tế**. Kết quả nhận dạng cần có thể kiểm tra lại bởi con người.

## 2. Mục tiêu

- Điều khiển mô hình đèn giao thông gồm LED đỏ, vàng và xanh bằng ESP32.
- Phát hiện phương tiện trong video hoặc hình ảnh.
- Theo dõi phương tiện qua các khung hình để hạn chế ghi nhận trùng.
- Xác định phương tiện có đi qua vạch dừng trong thời gian đèn đỏ hay không.
- Phát hiện vùng biển số và dùng OCR để đọc ký tự khi hình ảnh đủ rõ.
- Lưu thời gian, loại phương tiện, biển số, trạng thái đèn và đường dẫn ảnh bằng chứng.
- Xây dựng ứng dụng để xem, tìm kiếm/lọc và thống kê dữ liệu đã ghi nhận.

## 3. Công nghệ và quyết định kiến trúc

### Bắt buộc

- **Arduino IDE** để viết, biên dịch và nạp chương trình cho ESP32.
- **ESP32** điều khiển mô hình đèn giao thông.
- **Python** cho xử lý video, AI, logic vi phạm và tích hợp dữ liệu.
- Ứng dụng có giao diện để xem dữ liệu vi phạm là một phần của sản phẩm cuối. Giai đoạn đầu có thể chạy local trên laptop.

### Đề xuất ban đầu, có thể xem xét lại

| Thành phần               | Phương án khởi đầu              | Ghi chú                                                                                       |
| -------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Mô phỏng ESP32           | Wokwi                                 | Có thể dùng trước khi có phần cứng thật                                               |
| Đầu vào video           | Video có sẵn                        | Dễ kiểm thử và tái hiện lỗi; webcam làm sau                                            |
| Phát hiện phương tiện | YOLO bản nhỏ phù hợp              | Kiểm tra môi trường và giấy phép model trước khi chốt                                |
| Xử lý ảnh/video         | OpenCV                                | Đọc video, vẽ khung, cắt ảnh                                                              |
| Tracking                   | ByteTrack hoặc SORT                  | Chọn sau khi thử nghiệm                                                                     |
| Giao tiếp ESP32–laptop   | HTTP hoặc MQTT                       | Chưa chốt; chọn một phương án đơn giản, dễ kiểm thử                               |
| Phát hiện biển số      | Model phát hiện biển số phù hợp | Có thể cần model riêng ngoài model nhận diện xe                                         |
| OCR                        | EasyOCR, PaddleOCR hoặc Tesseract    | Thử trên dữ liệu thực tế trước khi chọn                                               |
| Cơ sở dữ liệu          | SQLite trước mắt; cân nhắc MySQL | Chưa phải quyết định cố định. Chọn theo yêu cầu triển khai và tích hợp          |
| Ứng dụng xem dữ liệu   | Streamlit local                       | Phương án nhanh để làm dashboard; có thể cân nhắc Flask/FastAPI + frontend nếu cần |
| Quản lý mã nguồn       | Git/GitHub                            | Không đưa mật khẩu, token hoặc dữ liệu nhạy cảm lên repo                            |

Không tự ý thay đổi yêu cầu bắt buộc dùng Arduino IDE. Những lựa chọn công nghệ còn lại cần được đánh giá và ghi lại lý do trước khi đổi.

## 4. Kiến trúc tổng quát

```text
ESP32 + 3 LED
    |
    | Trạng thái RED / YELLOW / GREEN
    | (HTTP hoặc MQTT — cần chốt sau khi đánh giá)
    v
Chương trình Python trên laptop <--- Video / webcam
    |
    +--> OpenCV đọc video
    +--> YOLO phát hiện phương tiện
    +--> Tracking gán ID phương tiện
    +--> Kiểm tra phương tiện đi qua vạch dừng
    +--> Đối chiếu trạng thái đèn và thời gian
    +--> Cắt ảnh xe / phát hiện biển số / OCR
    |
    v
Cơ sở dữ liệu + thư mục ảnh bằng chứng
    |
    v
Ứng dụng web local để xem, tìm kiếm và thống kê
```

Toàn bộ xử lý AI nên chạy local trên laptop ở giai đoạn đầu. Cloud, nhiều camera và app điện thoại là phần mở rộng, không làm trước khi luồng chính hoạt động ổn định.

## 5. Phần cứng dự kiến

- 1 ESP32 DevKit.
- 1 LED đỏ, 1 LED vàng, 1 LED xanh.
- Điện trở phù hợp, breadboard và dây jumper.
- Laptop để chạy Python, AI, cơ sở dữ liệu và ứng dụng.
- Video giao thông có sẵn; webcam là tùy chọn ở giai đoạn đầu.

Không cần bổ sung cảm biến siêu âm, hồng ngoại hoặc cảm biến ánh sáng cho phiên bản lõi nếu chưa có yêu cầu cụ thể. ESP32 đã biết trạng thái LED do chính nó điều khiển nên không cần LDR để suy ra màu đèn.

## 6. Lộ trình triển khai

### Giai đoạn 1 — Đèn giao thông

- Tạo project ESP32 trong Arduino IDE.
- Điều khiển lần lượt LED xanh, vàng, đỏ.
- Kiểm thử trên Wokwi nếu chưa có phần cứng.
- Ghi rõ sơ đồ chân GPIO và thời gian mỗi trạng thái.

### Giai đoạn 2 — Nhận diện xe từ video

- Thiết lập môi trường Python.
- Đọc video bằng OpenCV.
- Chạy model phát hiện phương tiện.
- Hiển thị bounding box và nhãn trên video.

### Giai đoạn 3 — Vạch dừng và tracking

- Cho phép cấu hình vạch dừng theo tọa độ trên video.
- Theo dõi xe qua nhiều frame.
- Xác định sự kiện xe đi qua vạch; tránh chỉ dựa vào một frame.
- Kiểm thử các tình huống xe dừng trước vạch, đi qua khi đèn xanh và đi qua khi đèn đỏ.

### Giai đoạn 4 — Kết nối trạng thái đèn

- Chốt HTTP hoặc MQTT sau khi so sánh độ phức tạp và nhu cầu.
- ESP32 gửi trạng thái và thời điểm chuyển trạng thái.
- Python nhận trạng thái đèn và đồng bộ timestamp.
- Nếu mất kết nối hoặc trạng thái không đáng tin cậy, đánh dấu `UNKNOWN`; không tự suy đoán là đèn đỏ.

### Giai đoạn 5 — Biển số và lưu dữ liệu

- Chỉ xử lý biển số khi có sự kiện nghi vi phạm.
- Cắt và lưu ảnh bằng chứng.
- Phát hiện vùng biển số, chạy OCR và chuẩn hóa chuỗi.
- Lưu thời gian, loại xe, biển số nhận dạng, trạng thái đèn, ảnh xe và ảnh biển số.
- Có cơ chế tránh lưu lặp cùng một xe/sự kiện.

### Giai đoạn 6 — Ứng dụng xem dữ liệu

Ứng dụng bản đầu nên chạy local và có:

- Trang tổng quan: tổng số bản ghi và thống kê cơ bản.
- Danh sách sự kiện: thời gian, biển số, loại xe, trạng thái đèn.
- Xem ảnh xe và ảnh biển số làm bằng chứng.
- Tìm kiếm/lọc theo biển số, ngày hoặc trạng thái.
- Hiển thị rõ các trường OCR không chắc chắn để người dùng kiểm tra.

Làm ứng dụng sau khi pipeline xử lý và lưu dữ liệu cơ bản đã chạy được, nhưng coi giao diện xem dữ liệu là mục tiêu bàn giao của dự án.

## 7. Cấu trúc thư mục gợi ý

Cấu trúc này là gợi ý ban đầu; có thể điều chỉnh sau khi kiểm tra repository hiện tại.

```text
iot-traffic/
├── README.md
├── CLAUDE.md
├── docs/
│   ├── SPECIFICATION.md
│   ├── ARCHITECTURE.md
│   └── DECISIONS.md
├── firmware/
│   └── esp32_traffic_light/
├── python/
│   ├── detection/
│   ├── tracking/
│   ├── violation/
│   ├── plate_ocr/
│   ├── storage/
│   └── app/
├── data/
│   ├── videos/          # Không commit video lớn nếu không cần
│   └── evidence/        # Cân nhắc .gitignore vì chứa dữ liệu hình ảnh
├── tests/
├── requirements.txt
├── .env.example
└── .gitignore
```

Không tạo lại hoặc di chuyển các thư mục hiện có một cách máy móc. Trước khi sửa cấu trúc, hãy kiểm tra repo và đề xuất thay đổi.

## 8. Tiêu chí MVP

MVP cần chứng minh được luồng chính:

1. ESP32 điều khiển đúng 3 LED bằng chương trình nạp qua Arduino IDE.
2. Laptop nhận được trạng thái đèn từ ESP32 qua giao thức đã chọn.
3. Chương trình phát hiện được phương tiện trong video.
4. Chương trình phát hiện được sự kiện đi qua vạch và đối chiếu trạng thái đèn.
5. Có thể nhận dạng biển số trong một số trường hợp hình ảnh đủ rõ.
6. Lưu được bản ghi và ảnh bằng chứng vào kho dữ liệu.
7. Ứng dụng hiển thị được bản ghi và ảnh, đồng thời hỗ trợ tìm kiếm/lọc cơ bản.

Độ chính xác hoàn hảo không được giả định. Cần báo cáo giới hạn, trường hợp nhận diện sai và kết quả kiểm thử.

## 9. Độ tin cậy, quyền riêng tư và an toàn

- Đồng bộ timestamp giữa trạng thái đèn và sự kiện video.
- Dùng ngưỡng confidence và giữ lại thông tin độ tin cậy khi phù hợp.
- Dùng tracking/event ID để hạn chế lưu nhiều lần cùng một sự kiện.
- Mất kết nối ESP32 thì dùng trạng thái `UNKNOWN`.
- Kiểm thử xe che khuất, biển số mờ, xe dừng sát vạch và xe qua vạch khi đèn xanh.
- Chỉ dùng video/ảnh phù hợp cho mục đích học tập; hạn chế chia sẻ công khai biển số và dữ liệu cá nhân.
- Không đưa mật khẩu, token, thông tin Wi-Fi thật vào mã nguồn.
- Kiểm tra giấy phép model, dataset và thư viện trước khi sử dụng hoặc công bố.

## 10. Phân công tham khảo cho 3 thành viên

| Thành viên | Phụ trách                    | Kết quả bàn giao                                                                     |
| ------------ | ------------------------------ | --------------------------------------------------------------------------------------- |
| 1            | IoT/ESP32                      | Mạch hoặc mô phỏng, code Arduino IDE, chu kỳ LED và giao tiếp trạng thái đèn |
| 2            | Phát hiện vi phạm           | Detection, tracking, cấu hình vạch dừng, logic crossing và ảnh xe                 |
| 3            | Biển số/dữ liệu/ứng dụng | Phát hiện biển số, OCR, lưu trữ và ứng dụng xem dữ liệu                      |

Các thành viên cần thống nhất giao diện giữa module, định dạng dữ liệu, timestamp và cách chạy project. Phân công có thể thay đổi theo năng lực và tiến độ.

## 11. Cách chạy dự án

Các lệnh cài đặt/chạy chính xác sẽ được bổ sung sau khi chọn thư viện, phiên bản Python, giao thức và database. Không nên viết lệnh giả định trước khi kiểm tra môi trường và mã nguồn thực tế.

## 12. Quy trình làm việc

1. Đọc `CLAUDE.md` và tài liệu trong `docs/` trước khi sửa code.
2. Xác định mục tiêu nhỏ, tiêu chí hoàn thành và cách kiểm thử.
3. Chỉ triển khai từng bước; không xây toàn bộ hệ thống trong một lần.
4. Sau mỗi bước, chạy kiểm thử và ghi lại kết quả thực tế.
5. Các quyết định về giao thức, database, model và framework phải được ghi trong `docs/DECISIONS.md` cùng lý do và đánh đổi.
6. Không tuyên bố chức năng đã hoàn thành nếu chưa chạy thử.
