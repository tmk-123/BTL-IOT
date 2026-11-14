# Demo IoT giao thông: camera, đèn MQTT, biển số và dashboard

**Cloud 15/11/2026:** đã có [đồng bộ SQLite/ảnh lên VPS và dashboard HTTPS có đăng nhập](docs/CLOUD.md) tại `https://jenkins.tienichnhanong.com/traffic/`, dùng trên điện thoại/máy tính. AI/MQTT tiếp tục chạy local; đồng bộ có gửi lại khi mất mạng và chống ghi trùng.

**Hướng dẫn demo cập nhật 05/11/2026:** xem [mục 11 — chạy từ đầu đến cuối](#11-cách-demo-từ-đầu-đến-cuối). Dùng ba cửa sổ PowerShell: broker MQTT, kiểm tra đèn/nhận diện, dashboard. Màu đèn lấy từ ESP32 điều khiển LED qua MQTT; hình ảnh lấy riêng từ ESP32-CAM qua HTTP.

Đã chạy chung camera thật + MQTT đèn thật + nhận diện xe/biển số + SQLite trong phiên 05/11. Có bản ghi qua vạch lúc đỏ với biển `29A22222` và ảnh bằng chứng. Đây là thử nghiệm trên mô hình, chưa phải đánh giá độ chính xác hay độ ổn định dài hạn. **Bộ đếm Nghi vượt đèn gộp các lượt qua lúc đỏ và vàng; bản ghi vẫn giữ màu đèn và lý do riêng.**

Đọc trước: [Định hướng và tiến độ](docs/DINH_HUONG_DU_AN.md) · [Các quyết định kỹ thuật](docs/DECISIONS.md).

Hướng dẫn: [Camera → Python](docs/CAMERA_PYTHON.md).

Chưa có LED/ESP32 đèn? [Bài thử camera + vạch + đèn MQTT giả lập](docs/MO_PHONG_KHONG_DEN.md): có bảng nút Xanh/Đỏ/Ngừng gửi, chọn vạch trên camera và xem kết quả trong vùng dữ liệu demo.

Nhận diện xe: [YOLO trên ảnh/video và ESP32-CAM](docs/YOLO.md).

Theo dõi xe và sự kiện qua vạch: [ByteTrack + vạch dừng](docs/TRACKING.md).

Trạng thái đèn: [MQTT → Python và ghép sự kiện](docs/MQTT_PYTHON.md). Tiến độ có bằng chứng: [CHECKLIST.md](CHECKLIST.md).

Logic nghi vượt đèn đỏ/vàng và demo 19 tình huống: [RED_LIGHT_LOGIC.md](docs/RED_LIGHT_LOGIC.md).

Lưu sự kiện và ảnh bằng chứng: [SQLite + JPEG](docs/STORAGE.md).

Xem dữ liệu trên trình duyệt laptop: [Giao diện Streamlit](docs/DASHBOARD.md).

- `firmware/testCamera/`, `firmware/testWiFi/`: các sketch camera và Wi-Fi đã chuyển từ thư mục gốc.
- `firmware/led_test/`, `firmware/esp32_traffic_light/`: firmware đèn.
- `python/camera_viewer.py`: nhận stream, hiển thị, nhấn S lưu ảnh.
- `docs/hardware/`: ảnh phần cứng.
- `data/snapshots/`: ảnh chụp, không đưa lên Git.

---

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

### Lựa chọn hiện tại

Trạng thái dưới đây được cập nhật theo luồng demo ngày 05/11/2026. Chi tiết và lý do trong [DECISIONS.md](docs/DECISIONS.md); chất lượng model trên dữ liệu thực tế vẫn cần đánh giá.

| Thành phần               | Phương án khởi đầu              | Ghi chú                                                                                       |
| -------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Mô phỏng ESP32           | Wokwi                                 | Có thể dùng trước khi có phần cứng thật                                               |
| Đầu vào video | ESP32-CAM qua HTTP/Wi-Fi | Đang dùng endpoint `/capture`; đã chạy cùng nhận diện |
| Phát hiện phương tiện | YOLOv8n | Đã chạy CPU với xe mô hình và ảnh/video mẫu |
| Xử lý ảnh/video         | OpenCV                                | Đọc video, vẽ khung, cắt ảnh                                                              |
| Tracking | ByteTrack | Đã có ID xe và phát hiện qua vạch |
| Trạng thái đèn ESP32–laptop | MQTT qua Mosquitto | Đã chốt; tách biệt với video HTTP |
| Phát hiện biển số | YOLOv9-t ONNX qua FastALPR | Detector riêng cho biển số |
| OCR | CCT-XS global ONNX qua FastALPR | Có bỏ phiếu qua nhiều ảnh, ghép với ID xe |
| Cơ sở dữ liệu | SQLite, ảnh lưu riêng | Đã lưu sự kiện, biển số và ảnh bằng chứng |
| Ứng dụng xem dữ liệu | Streamlit local | Có lọc, tìm biển số, xem ảnh và xuất CSV |
| Quản lý mã nguồn       | Git/GitHub                            | Không đưa mật khẩu, token hoặc dữ liệu nhạy cảm lên repo                            |

Không tự ý thay đổi yêu cầu bắt buộc dùng Arduino IDE. Những lựa chọn công nghệ còn lại cần được đánh giá và ghi lại lý do trước khi đổi.

## 4. Kiến trúc tổng quát

```text
ESP32 + 3 LED
    |
    | Trạng thái RED / YELLOW / GREEN
    | MQTT qua Mosquitto trên laptop — đã chốt
    v
Chương trình Python trên laptop <--- ESP32-CAM (HTTP stream)
    |
    +--> OpenCV đọc video
    +--> YOLOv8n phát hiện phương tiện
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
- ESP32-CAM làm nguồn hình hiện tại; video có sẵn có thể dùng để kiểm thử lặp lại.

Không cần bổ sung cảm biến siêu âm, hồng ngoại hoặc cảm biến ánh sáng cho phiên bản lõi nếu chưa có yêu cầu cụ thể. ESP32 đã biết trạng thái LED do chính nó điều khiển nên không cần LDR để suy ra màu đèn.

## 6. Lộ trình triển khai

Các mục dưới mô tả phạm vi chức năng. Thứ tự triển khai và tiến độ hiện tại theo [DINH_HUONG_DU_AN.md](docs/DINH_HUONG_DU_AN.md): hoàn tất camera → Python trước, sau đó nhận diện xe và tracking.

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

- Dùng MQTT đã chốt để truyền trạng thái đèn qua Mosquitto.
- ESP32 gửi trạng thái và thời điểm chuyển trạng thái.
- Python nhận trạng thái đèn và đồng bộ timestamp.
- Nếu mất kết nối hoặc trạng thái không đáng tin cậy, đánh dấu `UNKNOWN`; không tự suy đoán là đèn đỏ.

### Giai đoạn 5 — Biển số và lưu dữ liệu

- Đọc và ổn định biển số qua các frame khi bật `--plate-ocr`; lấy kết quả gắn với ID xe ngay lúc qua vạch.
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

## 11. Cách demo từ đầu đến cuối

### 11.1. Chuẩn bị trước khi mở chương trình

- Cấp nguồn cho **hai board riêng**: ESP32-CAM quay hình và ESP32 DevKit điều khiển ba LED. Phát triển/nạp firmware bằng **Arduino IDE**.
- Laptop, ESP32 đèn và ESP32-CAM kết nối cùng mạng Wi-Fi 2,4 GHz, cho phép các thiết bị liên lạc với nhau.
- Máy đang demo đã có `.venv`, model và Mosquitto. Các lệnh dưới gọi thẳng Python trong `.venv`, không cần activate và không cần cài lại thư viện mỗi buổi. Máy mới xem [cài môi trường camera](docs/CAMERA_PYTHON.md), [OCR kết hợp](docs/BIEN_SO.md#bước-5--biển-số-trong-sự-kiện-sqlite-và-streamlit) và [cài broker/tài khoản](firmware/esp32_traffic_light/README.md#3-chuẩn-bị-broker-mosquitto-trên-laptop-làm-một-lần).
- Đóng Plate scanner, chương trình mô phỏng và các cửa sổ nhận diện cũ trước khi chạy. Đóng tab đang xem stream camera; chỉ để một chương trình Python đọc camera trong bài demo.
- Mở **ba cửa sổ PowerShell**. Trong mỗi cửa sổ chạy:

```powershell
cd D:\Ki1_4\IOT\BTL
```

**Kiểm tra lại IP mỗi khi đổi Wi-Fi/hotspot.** Trong một PowerShell chạy:

```powershell
Get-NetIPAddress -InterfaceAlias "Wi-Fi" -AddressFamily IPv4 | Select-Object IPAddress
```

Các địa chỉ đã dùng ngày 05/11/2026:

| Thành phần | Địa chỉ | Dùng ở đâu |
| --- | --- | --- |
| Laptop trên Wi-Fi | `10.82.212.75` | `MQTT_HOST` trong firmware ESP32 đèn |
| ESP32-CAM | `10.82.212.69` | URL `/capture` cho Python |
| Broker nhìn từ Python trên laptop | `127.0.0.1:1883` | Tham số `--mqtt-host` / `--mqtt-port` |
| Dashboard trên laptop | `http://127.0.0.1:8501` | Mở bằng trình duyệt |

Trong Arduino IDE, mở sketch `firmware/esp32_traffic_light/esp32_traffic_light.ino`, kiểm tra file `secrets.h`:

```cpp
// Thay bằng IPv4 Wi-Fi hiện tại của laptop.
#define MQTT_HOST "10.82.212.75"
```

Wi-Fi và tài khoản MQTT trong `secrets.h` phải khớp mạng/broker đang dùng. Nếu vừa sửa file, nhấn **Upload** để board nhận cấu hình mới. Không dùng IP camera hoặc `127.0.0.1` làm `MQTT_HOST` trên ESP32. Không đưa mật khẩu vào README hay command line.

Lấy IP camera từ Serial Monitor của sketch camera. Mở `http://10.82.212.69/`, chọn **VGA (640×480)** trước khi chạy nhận diện; không đổi độ phân giải trong lúc tracking. Nếu IP camera khác, thay URL ở các lệnh phía dưới. Căn camera cố định, thấy được cả xe trước vạch, sau vạch và biển số rõ.

### 11.2. PowerShell 1 — bật broker MQTT thật

Chạy từ thư mục gốc dự án và để cửa sổ này mở:

```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -c tools\mosquitto\mosquitto.conf -v
```

Thấy `Opening ipv4 listen socket on port 1883` và `mosquitto ... running` là broker đã khởi động. Cấu hình này cần file tài khoản `tools/mosquitto/passwd` đã tạo trước đó, với các tài khoản `esp32` và `laptop`.

Broker thật **không tự bật từ `vehicle_detector.py`**. Nếu báo cổng đang được dùng, kiểm tra broker cũ thay vì mở thêm một bản:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 1883 | Select-Object LocalAddress,LocalPort,OwningProcess
```

Trong Serial Monitor ESP32 đèn (115200 baud), chờ `MQTT: da ket noi` và `wifi=on mqtt=on`. Nếu Wi-Fi đã kết nối nhưng `mqtt=off`, xem phần xử lý lỗi bên dưới trước khi chạy nhận diện.

### 11.3. PowerShell 2 — xác nhận Python nhận đúng đèn thật

```powershell
.\.venv\Scripts\python.exe -u -B python/mqtt_light.py --mqtt-host 127.0.0.1 --mqtt-port 1883 --mqtt-user laptop
```

Nhập mật khẩu của tài khoản **laptop** khi được hỏi; ký tự mật khẩu không hiện trên màn hình. Không phải mật khẩu Wi-Fi. Chờ ít nhất một chu kỳ đèn; kết quả phải đổi theo LED thật:

```text
MQTT: connected; subscribed to lamp state/status
LIGHT: GREEN
LIGHT: YELLOW
LIGHT: RED
```

Chu kỳ firmware hiện tại: **xanh 10 giây → vàng 3 giây → đỏ 10 giây**. Ban đầu `LIGHT: UNKNOWN` khi chưa nhận bản tin mới là bình thường. Khi đã xác nhận màu đổi đúng, nhấn **Ctrl+C** dừng bộ kiểm tra rồi dùng tiếp cửa sổ này cho bước 11.4.

### 11.4. PowerShell 2 — chạy nhận diện xe, biển số và vượt vạch

```powershell
.\.venv\Scripts\python.exe -u -B python/vehicle_detector.py --source http://10.82.212.69/capture --snapshot --async-snapshot --track --select-line --plate-ocr --plate-max-gap 1.5 --mqtt-host 127.0.0.1 --mqtt-port 1883 --mqtt-user laptop --save-all-evidence
```

Nhập lại mật khẩu MQTT của tài khoản `laptop` khi được hỏi. Luồng này dùng topic mặc định `traffic/inter1/light` và thiết bị `esp32-inter1`, tương ứng firmware đèn thật. Không thêm `--simulation` vào lệnh này.

`--async-snapshot` lấy ảnh trong luồng riêng trong lúc AI xử lý và chỉ giữ ảnh mới nhất, không tích hàng đợi ảnh cũ. Timestamp sự kiện lấy lúc nhận ảnh, không lấy lúc AI xử lý xong. Nếu có lần đọc ảnh lỗi, lịch sử crossing/OCR được xóa kể cả khi ảnh mới đã về trước khi AI đọc được báo lỗi. Bỏ tùy chọn này để quay lại đọc ảnh tuần tự.

**Nếu FPS thấp:** dùng VGA 640×480 và JPEG Quality khoảng 12 trên trang camera, đặt trước khi chọn vạch. Không đổi độ phân giải khi tracking đang chạy. Lần đo trên máy i7-6600U cho thấy ảnh HD 1280×720/quality 4 mất khoảng 0,39–0,58 giây để tải mỗi ảnh; giảm `--imgsz` YOLO xuống 416/320 đã bỏ sót xe mô hình trong 8 ảnh thử, nên giữ mặc định 640 cho bài demo này. FPS vẫn phụ thuộc Wi-Fi, CPU và độ rõ của biển số.

Trong cửa sổ chọn vạch:

1. Căn camera và để xe ở **trước vạch**, trong vùng hình có thể nhận diện.
2. Click hai đầu vạch theo thứ tự **trái sang phải**. Click đầu tiên đóng băng ảnh để chọn điểm thứ hai.
3. Nhấn **Enter** để bắt đầu. Nhấn **R** nếu cần xóa điểm và căn lại; **Q** hủy.
4. Kiểm tra có khung xe, ID và `Light` đổi tương ứng LED thật. Điểm xét qua vạch là **giữa cạnh dưới khung xe**, không phải biển số hay đầu xe.

Demo mặc định **không lọc chiều**: mọi lượt xe qua vạch đều xét màu đèn (`--violation-direction both`). Cần có ID xe liên tục ở cả hai phía vạch; đọc được biển số riêng chưa đủ để tạo sự kiện. Vì không lọc chiều, khi đưa xe trở lại qua vạch lúc đỏ/vàng cũng có thể tăng bộ đếm; muốn chỉ demo một lượt, nhấc xe về điểm xuất phát ngoài khung hình rồi bắt đầu lượt mới.

`--save-all-evidence` lưu ảnh cho mọi crossing, tiện đối chiếu cả xanh/UNKNOWN; không thay đổi kết quả phân loại. Nếu chỉ muốn lưu ảnh nghi vượt đèn đỏ/vàng, bỏ tùy chọn này. Trong cửa sổ YOLO, **S** lưu thêm ảnh thủ công, **Q** dừng nhận diện. Muốn chọn lại vạch, Q rồi chạy lại lệnh.

### 11.5. PowerShell 3 — mở dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run python/dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Mở **http://127.0.0.1:8501** bằng trình duyệt. Giữ cửa sổ PowerShell 3 mở.

1. Mặc định dùng **Dữ liệu chạy thật** (đọc `data/traffic.db`); muốn đổi nguồn, mở **Cài đặt → Chọn dữ liệu**.
2. Màn hình chính chỉ hiện nghi đỏ/vàng và một ô **Tổng lượt nghi vượt đèn**. Muốn xem xanh/UNKNOWN hoặc bản ghi cũ, mở **Nhật ký kiểm tra → Xem tất cả sự kiện**.
3. Sau mỗi lượt xe qua, nhấn **Làm mới dữ liệu**.
4. Bấm vào dòng có biển số/thời gian cần xem để mở **Chi tiết vi phạm**: ảnh ghi nhận tại vạch, biển số, màu đèn và thời gian. Mở **Xem ảnh gốc và ảnh xe** nếu muốn đối chiếu thêm; đóng hộp bằng dấu X để chọn lượt khác. Giao diện không hiển thị JSON.
5. Nhập `29A22222` để tìm biển mô hình đã demo, hoặc chọn **Màu đèn → Vàng** để xem riêng các lượt vàng. Phân trang ở cuối danh sách khi quá 25 lượt; mở **Xuất dữ liệu → Tải CSV trang hiện tại** để xuất các dòng đang xem.

Dashboard hiển thị sự kiện đã lưu, không hiển thị trực tiếp màu LED và không tự làm mới. Database giữ các phiên cũ; dùng thời gian ghi nhận để phân biệt lượt test mới. Nếu cổng 8501 đã có dashboard đang chạy, mở trang đó; nếu là ứng dụng khác, đổi `--server.port 8502` và mở `http://127.0.0.1:8502`.

### 11.6. Kịch bản demo và kết quả cần đối chiếu

Mỗi lượt bắt đầu với xe trước vạch và đã có ID. Thử **xanh trước, đỏ sau**, rồi vàng và mất kết nối. Với lượt đỏ, chờ đèn đỏ ổn định khoảng 2 giây trước khi đưa xe qua, tránh thời điểm vừa đổi màu. Không loại lượt qua vạch vì hướng đi trong cấu hình demo mặc định.

| Tình huống | Thao tác | Kết quả hiện tại |
| --- | --- | --- |
| Qua vạch lúc xanh | Cho xe qua khi GREEN liên tục | `no_red_light_evidence` — không có bằng chứng đèn đỏ |
| Qua vạch lúc đỏ | Cho xe qua khi RED liên tục | `suspected_red_light` — nghi vượt đèn đỏ; bộ đếm chung tăng |
| Dừng trước vạch lúc đỏ | Giữ xe trước vạch, không đổi phía | Không có crossing mới |
| Qua vạch lúc vàng | Cho xe qua khi YELLOW liên tục trong khoảng xét | `suspected_yellow_light` — nghi vượt đèn vàng; bộ đếm chung tăng, lưu ảnh như lượt nghi đỏ |
| Đổi màu giữa lúc qua | Xe qua gần lúc xanh/vàng/đỏ chuyển trạng thái | `unverified` nếu khoảng xét chứa nhiều màu hoặc thiếu dữ liệu |
| Mất trạng thái đèn | Rút nguồn ESP32 **đèn**, giữ camera hoạt động; chờ >1,5 giây rồi cho xe qua | `Light: UNKNOWN`, crossing là `unverified`, không tăng bộ đếm nghi vượt đèn |
| Qua vạch theo hướng trở lại | Đưa xe đổi phía qua vạch | Vẫn xét đỏ/vàng/xanh/UNKNOWN giống hướng đi tới |

Đèn vàng chỉ có 3 giây và thuật toán cần một màu liên tục trong cả khoảng qua vạch, thêm 0,5 giây dự phòng phía trước. Vì vậy lượt qua sát thời điểm đổi màu có thể là `unverified`; không mặc định mọi lượt thấy vàng đều được xác nhận YELLOW. Đây là chính sách demo ghi nhận nghi vượt đèn để xem lại ảnh/thời điểm. Những sự kiện vàng lưu bằng phiên bản cũ vẫn giữ kết quả cũ, không tự đổi nhãn; cần chạy lại nhận diện để áp dụng logic mới cho các lượt tiếp theo.

Đọc các dòng trên cửa sổ YOLO:

- **Crossings**: số lượt qua vạch đã ghi trong phiên, có thể gồm cả hai chiều.
- **Light**: màu đèn nhận từ MQTT hiện tại.
- **Suspected red/yellow-light**: tổng lượt nghi vượt đèn đỏ **hoặc vàng** trong phiên. Đèn đã chuyển xanh thì số này vẫn giữ nguyên; kiểm tra màu **tại thời điểm sự kiện** trên dashboard.
- **Plate: pending / PENDING**: OCR hiện tại chưa đủ đồng thuận hoặc còn mơ hồ. Biển trong bản ghi được chốt tại crossing; OCR đọc rõ hơn sau đó không tự điền ngược vào sự kiện cũ.

Lượt test cơ bản đạt khi: LED và `Light` đổi khớp; qua đỏ/vàng liên tục làm tăng bộ đếm chung; qua xanh không tăng bộ đếm; dừng trước vạch không có crossing; mất MQTT về UNKNOWN; sự kiện và ảnh mở được trên dashboard. Lặp lại các lượt để kiểm tra tính ổn định; một lượt thành công chưa phải đo độ chính xác toàn hệ thống.

### 11.7. Xem dữ liệu bằng lệnh và kết thúc demo

Nếu muốn kiểm tra database không qua giao diện, mở thêm PowerShell tại gốc dự án:

```powershell
.\.venv\Scripts\python.exe python/list_events.py --limit 5
.\.venv\Scripts\python.exe python/list_events.py --assessment suspected_red_light --limit 5
.\.venv\Scripts\python.exe python/list_events.py --assessment suspected_yellow_light --limit 5
```

| Dữ liệu | Nơi lưu |
| --- | --- |
| Sự kiện và biển số | `data/traffic.db` |
| Ảnh bằng chứng từng sự kiện | `data/evidence/<mã-băm>/` |
| Log crossing và ảnh nhấn S | `data/detections/` |
| Ảnh từ Plate scanner riêng | `data/plates/` — không tự trở thành sự kiện vượt đèn |

Kết thúc theo thứ tự: **Q** ở cửa sổ nhận diện → **Ctrl+C** ở PowerShell dashboard → **Ctrl+C** ở PowerShell broker. Dữ liệu đã lưu được giữ lại; chạy lại tạo phiên mới, bộ đếm trên cửa sổ YOLO bắt đầu lại từ 0.

### 11.8. Lỗi thường gặp trong buổi demo

| Hiện tượng | Kiểm tra / cách xử lý |
| --- | --- |
| ESP32 `wifi=on mqtt=off`, kết nối thất bại | Bật broker cổng 1883; kiểm tra `MQTT_HOST` là IPv4 Wi-Fi hiện tại của laptop; sửa rồi Upload lại. Kiểm tra tài khoản và kết nối LAN/firewall theo [hướng dẫn broker](firmware/esp32_traffic_light/README.md). |
| Python báo kết nối MQTT bị từ chối | Nhập đúng mật khẩu tài khoản `laptop`; kiểm tra file `tools/mosquitto/passwd` của broker. |
| LED đổi nhưng Light luôn GREEN, có dòng SIMULATION | Đang chạy `traffic_demo.py`/nguồn đèn giả lập. Đóng mô phỏng và chạy lệnh ở bước 11.4; broker giả lập tự mở cổng riêng, không chứng minh ESP32 đèn thật đã kết nối. |
| Light UNKNOWN liên tục | Chưa có bản tin mới, sai topic/device, ESP32 mất kết nối hoặc heartbeat hết hạn. Quay lại bước 11.3; không coi UNKNOWN là đỏ. |
| Camera timeout | Kiểm tra nguồn, IP và Wi-Fi; đóng các chương trình/tab khác đang đọc camera, rồi chạy lại. |
| Đọc được biển nhưng Crossings không tăng | Kiểm tra có khung và ID **xe**, vị trí giữa đáy khung đã đổi phía qua đoạn vạch và ID không bị mất. |
| Qua lúc đỏ nhưng chưa xác minh | Có thể vừa đổi đèn, mất heartbeat hoặc thiếu lịch sử trước vạch. Để xe trước vạch, chờ đỏ ổn định rồi thử lại. |
| Không có sự kiện trên dashboard | Mở Cài đặt kiểm tra nguồn Dữ liệu chạy thật; bật Nhật ký kiểm tra → Xem tất cả sự kiện, bấm Làm mới dữ liệu và bỏ bộ lọc/tìm kiếm cũ. |
| OpenCV báo không hỗ trợ `imshow`/`namedWindow` | Đang dùng bản headless hoặc môi trường khác. Máy demo hiện dùng `.venv` có WIN32UI; xem [ghi chú môi trường OCR](docs/BIEN_SO.md), không cài lại thư viện khi camera đang chạy. |

**Bài demo không có đèn thật:** dùng [hướng dẫn mô phỏng riêng](docs/MO_PHONG_KHONG_DEN.md). `traffic_demo.py` tự bật broker nội bộ và gửi màu bằng nút bấm; dữ liệu nằm ở `data/demos/live_simulation/`, dashboard chọn **Camera + đèn giả lập**. Không dùng các lệnh mô phỏng để kiểm tra LED thật.

## 12. Quy trình làm việc

1. Đọc `CLAUDE.md` và tài liệu trong `docs/` trước khi sửa code.
2. Xác định mục tiêu nhỏ, tiêu chí hoàn thành và cách kiểm thử.
3. Chỉ triển khai từng bước; không xây toàn bộ hệ thống trong một lần.
4. Sau mỗi bước, chạy kiểm thử và ghi lại kết quả thực tế.
5. Các quyết định về giao thức, database, model và framework phải được ghi trong `docs/DECISIONS.md` cùng lý do và đánh đổi.
6. Không tuyên bố chức năng đã hoàn thành nếu chưa chạy thử.
