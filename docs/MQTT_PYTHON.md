# Nhận trạng thái đèn và ghép sự kiện qua vạch

Mốc này bổ sung phần Python, giữ nguyên firmware. ESP32-CAM gửi ảnh HTTP; một ESP32 DevKit riêng chạy sketch đèn và gửi MQTT. Không nạp firmware đèn lên ESP32-CAM đang dùng để quay hình.

## Đã làm gì

Logic được bổ sung lý do phân loại và demo không cần phần cứng tại [RED_LIGHT_LOGIC.md](RED_LIGHT_LOGIC.md). Bộ kiểm thử hiện tại có 33 bài đạt; con số 28 bên dưới là kết quả mốc MQTT ban đầu.

- `python/mqtt_light.py`: nhận hai topic `/state`, `/status` theo firmware hiện có; tự kết nối lại và đăng ký lại topic.
- `python/light_state.py`: kiểm tra JSON, device, seq, uptime, thời gian đèn; chỉ tin bản tin mới. Mặc định quá 1.5 giây không có heartbeat thì UNKNOWN; cũng hết hiệu lực khi đã hết thời gian màu đèn ghi trong bản tin. Timeout có thể chỉnh bằng `--light-timeout`.
- `vehicle_detector.py`: hiển thị màu đèn, đối chiếu khoảng từ điểm ổn định trước vạch đến frame xác nhận đã qua vạch. Chỉ ghi `suspected_red_light` khi đỏ còn hiệu lực liên tục, đúng chiều đã cấu hình. Khoảng thiếu dữ liệu, đổi màu hoặc mất kết nối được để `unverified`.
- JSONL bổ sung `light_state`, `assessment`, `crossing_window_s`, `timing_margin_s`. Vẫn ghi cả crossing xanh/vàng/UNKNOWN để kiểm tra. SQLite và ảnh đã được bổ sung ở mốc [STORAGE.md](STORAGE.md); OCR chưa triển khai.

## Thử MQTT không cần ESP32

Mở **ba cửa sổ PowerShell**, tất cả tại thư mục gốc dự án. Bộ chạy broker đã có tại `C:\Program Files\mosquitto\mosquitto.exe` trên máy này. Dùng cổng **18884**, chỉ lắng nghe trên chính laptop; không cần tài khoản cho bài thử này và không dùng cấu hình này cho ESP32 qua LAN.

**Cửa sổ 1 — bật broker thử:**

```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -c tools/mosquitto/local-test.conf -v
```

**Cửa sổ 2 — xem màu đèn Python nhận được:**

```powershell
.\.venv\Scripts\python.exe python/mqtt_light.py --mqtt-host 127.0.0.1 --mqtt-port 18884 --mqtt-topic demo/inter1/light
```

Ban đầu thấy `LIGHT: UNKNOWN` là đúng vì chưa có nguồn gửi.

**Cửa sổ 3 — giả lập đèn đỏ trong 15 giây:**

```powershell
.\.venv\Scripts\python.exe python/mqtt_simulator.py --state RED --seconds 15
```

Cửa sổ 2 cần hiện `LIGHT: RED`, rồi `LIGHT: UNKNOWN` khi giả lập kết thúc. Thử lại với `--state GREEN` và `--state YELLOW`. Ctrl+C cửa sổ 1: bộ nhận phải về UNKNOWN; mở lại broker rồi chạy lại simulator: bộ nhận tự kết nối lại.

Đây là **bản tin giả lập**, không điều khiển LED và chưa chứng minh ESP32 thật hoạt động.

## ESP32 và broker thật

1. Dùng ESP32 DevKit điều khiển LED, xác nhận chân và đấu dây theo [firmware README](../firmware/esp32_traffic_light/README.md). GPIO mẫu chưa phải xác nhận đấu mạch thực tế.
2. Làm theo hướng dẫn broker **có tài khoản** trong firmware README. Chạy từ thư mục repository hiện tại; không dùng đường dẫn D: hoặc IP máy khác được ghi trong hướng dẫn cũ.
3. Điền Wi-Fi/broker trong `secrets.h` cục bộ của sketch đèn; `MQTT_HOST` trên ESP32 là **IPv4 hiện tại của laptop**, không phải IP camera hoặc 127.0.0.1. Nạp qua Arduino IDE. Mật khẩu không đưa lên Git.
4. Mở broker bằng `tools/mosquitto/mosquitto.conf` (cổng 1883, yêu cầu `tools/mosquitto/passwd`). Cấu hình firewall/mạng LAN và tài khoản cần kiểm tra trực tiếp, chưa được thiết lập tự động trong mốc này.
5. Kiểm tra màu đèn trước khi mở camera:

```powershell
.\.venv\Scripts\python.exe python/mqtt_light.py --mqtt-host 127.0.0.1 --mqtt-user laptop
```

Python hỏi mật khẩu, ký tự nhập được ẩn. Có thể dùng biến môi trường `MQTT_USER`, `MQTT_PASSWORD` thay cho lời nhắc; không truyền mật khẩu trực tiếp trong command line.

Đèn LED đổi màu thì `LIGHT` cần đổi tương ứng. Rút nguồn ESP32: về UNKNOWN khi hết heartbeat, không phải đợi Last Will.

## Ghép với camera và vạch

Chỉ làm sau khi nhận đèn thật đúng và camera `/capture` mở được. Đóng chương trình khác đang đọc camera.

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source http://10.82.212.69/capture --snapshot --select-line --mqtt-host 127.0.0.1 --mqtt-user laptop
```

Thay IP camera nếu đã đổi. Bấm hai đầu vạch từ trái sang phải, Enter để chạy. Mặc định nghi vượt đèn đỏ chỉ xét chiều **trên xuống dưới**; đổi chiều với `--violation-direction positive_to_negative`. `--direction` vẫn là bộ lọc chiều của các crossing nói chung.

Kết quả:

| assessment | Ý nghĩa |
| --- | --- |
| `suspected_red_light` | Qua vạch đúng chiều trong khoảng có dữ liệu đỏ liên tục; cần người kiểm tra |
| `suspected_yellow_light` | Qua vạch đúng chiều trong khoảng vàng liên tục; cộng cùng bộ đếm nghi vượt đèn với đỏ (cập nhật 05/11/2026) |
| `no_red_light_evidence` | Dữ liệu xanh liên tục; không có bằng chứng đỏ |
| `unverified` | Thiếu dữ liệu đèn, hết hạn hoặc đổi màu trong khoảng theo dõi |
| `not_applicable_direction` | Xe đi chiều không dùng để xét nghi vượt đèn đỏ |

**Giới hạn thời gian:** chưa đồng bộ đồng hồ camera/ESP32. Dùng thời gian laptop nhận frame và bản tin, không phải thời điểm phơi sáng thực. Mặc định mở rộng phía trước khoảng crossing thêm 0.5 giây (`--timing-margin`) để giảm đánh dấu nhầm gần lúc đổi đèn; đây là cấu hình thử, không bảo đảm bù mọi độ trễ. Cần đo/đánh giá lại khi mạng giật hoặc dùng snapshot chậm. Không ghép MQTT trực tiếp với video ghi sẵn, vì hai nguồn không cùng thời gian; CLI chủ động từ chối trường hợp đó.

## Kiểm thử đã chạy

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

28 kiểm thử đạt ngày 02/11/2026: 11 vạch dừng, 16 logic màu đèn/phân loại và 1 bài tích hợp dùng Mosquitto thật trên loopback với cổng tạm. Bài tích hợp kiểm tra màu đỏ/xanh/vàng, retained, heartbeat timeout, offline, tắt broker và tự kết nối lại/nhận màu mới. Broker và client của bài test tự dọn sau khi chạy. Nếu máy khác chưa cài Mosquitto, bài tích hợp được đánh dấu SKIP, không được coi là đã đạt.

Video tổng hợp 41 frame vẫn tạo đúng 1 crossing UNKNOWN/unverified khi không bật MQTT. Chưa xác nhận bộ camera + ESP32 đèn thật + mạng LAN chạy cùng nhau, chưa kiểm tra độ trễ ngoài thực tế.

API sử dụng theo tài liệu Eclipse Paho: https://eclipse.dev/paho/clients/python/docs/ .
