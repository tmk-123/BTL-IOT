# ESP32 Traffic Light — Bước 1b (Wi-Fi + MQTT)

3 LED chạy chu kỳ **Xanh 10 s → Vàng 3 s → Đỏ 10 s**, đồng thời gửi trạng thái đèn lên **MQTT broker**
(Mosquitto chạy trên laptop). Đèn **không phụ thuộc mạng**: mất Wi-Fi/broker thì đèn vẫn chạy.

| File | Vai trò |
|---|---|
| `esp32_traffic_light.ino` | Chương trình chính: máy trạng thái đèn (`millis()`) + Wi-Fi + MQTT |
| `config.h` | GPIO, thời gian đèn, topic, chu kỳ heartbeat — **sửa ở đây** |
| `secrets.example.h` | Mẫu thông tin Wi-Fi / broker. Copy thành `secrets.h` rồi điền |
| `secrets.h` | Thông tin thật — **không đưa lên Git** (đã có trong `.gitignore`) |
| `diagram.json` | Sơ đồ mạch cho Wokwi |

> Arduino IDE yêu cầu tên thư mục trùng tên file `.ino` (`esp32_traffic_light`).

---

## 0. Chuẩn bị Arduino IDE (làm một lần)

### 0.1. Sketchbook phải nằm ở đường dẫn KHÔNG dấu

Trình biên dịch ESP32 **lỗi khi đường dẫn thư viện có ký tự tiếng Việt**. Trên máy hiện tại sketchbook là
`C:\Users\ADMIN\OneDrive\Tài liệu\Arduino` → sẽ báo `fatal error: PubSubClient.h: No such file or directory`.

Sửa: **File → Preferences → Sketchbook location** → đổi thành `C:\Arduino` (hoặc `D:\Arduino`) → OK → khởi động lại Arduino IDE.

### 0.2. Cài thư viện

**Tools → Manage Libraries…** → tìm `PubSubClient` → chọn bản của **Nick O'Leary** (giấy phép MIT) → Install.
(Cài sau khi đổi sketchbook để thư viện nằm trong thư mục mới.)

### 0.3. Board

**Tools → Board → esp32 → ESP32 Dev Module**; **Tools → Port** → cổng COM của ESP32.

---

## 1. Đấu dây

| LED | GPIO | Đấu |
|---|---|---|
| Đỏ | 25 | GPIO25 → điện trở 220 Ω → chân **dài** LED; chân **ngắn** → GND |
| Vàng | 26 | GPIO26 → điện trở 220 Ω → chân dài LED; chân ngắn → GND |
| Xanh | 27 | GPIO27 → điện trở 220 Ω → chân dài LED; chân ngắn → GND |

**Bắt buộc có điện trở.** GPIO 25/26/27 là giả định (DECISIONS D-10); đổi chân → sửa `config.h`.

---

## 2. Dữ liệu ESP32 gửi đi (hợp đồng MQTT)

| Topic | Payload | Retained | Khi nào gửi |
|---|---|---|---|
| `traffic/inter1/light/state` | JSON (dưới đây) | Không | Khi đổi đèn (`change`), mỗi 1 s (`heartbeat`), khi vừa kết nối (`connect`) |
| `traffic/inter1/light/status` | `online` / `offline` | Có | `online` khi kết nối; `offline` do broker tự gửi (**Last Will**) khi ESP32 mất kết nối |

```json
{"device":"esp32-inter1","state":"RED","seq":3,"ms_in_state":1830,
 "duration_ms":10000,"uptime_ms":15033,"reason":"heartbeat"}
```

| Trường | Ý nghĩa |
|---|---|
| `state` | `GREEN` / `YELLOW` / `RED` (ESP32 không bao giờ gửi `UNKNOWN`; `UNKNOWN` do laptop tự suy ra) |
| `seq` | Tăng 1 mỗi lần đổi đèn. Nhảy cóc → laptop biết đã mất bản tin |
| `ms_in_state` | Đèn hiện tại đã sáng bao lâu. Laptop tính: *thời điểm đổi đèn = lúc nhận − ms_in_state* |
| `duration_ms` | Tổng thời gian của đèn hiện tại |
| `uptime_ms` | `millis()` của ESP32 — chỉ để debug; giảm về nhỏ → ESP32 vừa khởi động lại |
| `reason` | `change` / `heartbeat` / `connect` |

**Quy tắc phía laptop** (sẽ làm ở GĐ 4): quá **1,5 s** không nhận bản tin `state`, hoặc `status` = `offline`
→ trạng thái `UNKNOWN`.

> PubSubClient chỉ publish được **QoS 0**. Mạng LAN dùng TCP nên hiếm mất tin; nếu mất, heartbeat 1 s và `seq` bù lại.

---

## 3. Chuẩn bị broker Mosquitto trên laptop (làm một lần)

Máy đã cài Mosquitto 2.1.2 tại `C:\Program Files\mosquitto`. Service Windows `mosquitto` đang chạy với cấu hình
mặc định **chỉ nhận kết nối từ chính laptop** → ESP32 không vào được. Ta chạy broker bằng file cấu hình riêng của dự án.

Mở **PowerShell bằng Run as Administrator**:

```powershell
# 3.1. Dừng service mặc định để giải phóng cổng 1883, và không tự chạy lại khi khởi động máy
Stop-Service mosquitto
Set-Service mosquitto -StartupType Manual

# 3.2. Mở cổng 1883 cho mạng Private
New-NetFirewallRule -DisplayName "Mosquitto MQTT 1883 (IoT BTL)" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow -Profile Private

# 3.3. Kiểm tra mạng Wi-Fi đang là Private hay Public
Get-NetConnectionProfile
```

Nếu `NetworkCategory` là `Public`: vào **Settings → Network & Internet → Wi-Fi → (tên mạng) → Private network**.
Không mở cổng cho mạng Public (quán cà phê, Wi-Fi công cộng).

Mở PowerShell thường, **tại thư mục gốc dự án** `D:\Ki1_4\IOT\BTL`:

```powershell
# 3.4. Tạo tài khoản (lệnh hỏi mật khẩu). -c = tạo file mới, chỉ dùng cho lần đầu.
& "C:\Program Files\mosquitto\mosquitto_passwd.exe" -c tools\mosquitto\passwd esp32
& "C:\Program Files\mosquitto\mosquitto_passwd.exe" tools\mosquitto\passwd laptop
```

`esp32` dùng cho ESP32 (ghi vào `secrets.h`), `laptop` dùng cho Python và lệnh test.

---

## 4. Chạy và kiểm thử

### 4.1. Bật broker (cửa sổ 1, tại `D:\Ki1_4\IOT\BTL`, để mở suốt buổi)

```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -c tools\mosquitto\mosquitto.conf -v
```

Thấy `Opening ipv4 listen socket on port 1883` là được.

### 4.2. Theo dõi tin nhắn (cửa sổ 2)

```powershell
& "C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -u laptop -P <mat_khau_laptop> -t "traffic/#" -v
```

### 4.3. Thử broker trước khi có ESP32 (cửa sổ 3)

```powershell
& "C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -u laptop -P <mat_khau_laptop> -t "traffic/inter1/light/state" -m "test"
```

Cửa sổ 2 in `traffic/inter1/light/state test` → broker hoạt động.

### 4.4. Nạp ESP32

1. Copy `secrets.example.h` → `secrets.h` (đã có sẵn bản placeholder, chỉ cần sửa).
2. Điền `WIFI_SSID`, `WIFI_PASSWORD` (mạng **2,4 GHz**, laptop và ESP32 **cùng mạng**),
   `MQTT_HOST` = IPv4 của laptop (lệnh `ipconfig`, mục *Wireless LAN adapter Wi-Fi*; lúc kiểm tra là `10.137.219.75`,
   có thể đổi khi đổi mạng), `MQTT_USER` = `esp32`, `MQTT_PASSWORD` = mật khẩu đã đặt.
3. Arduino IDE: Verify → Upload → Serial Monitor 115200.

### 4.5. Kết quả mong đợi

Serial Monitor:
```text
=== ESP32 Traffic Light - buoc 1b (Wi-Fi + MQTT) ===
...
[t=203 ms] seq=1 state=GREEN duration=10000 ms
[t=1203 ms] state=GREEN ms_in_state=1000 remaining=9000 ms | wifi=off mqtt=off
[t=2911 ms] WiFi: da ket noi, IP ESP32 = 10.137.219.xx
[t=5003 ms] MQTT: ket noi 10.137.219.75:1883 ...
[t=5051 ms] MQTT: da ket noi
[t=6203 ms] state=GREEN ms_in_state=6000 remaining=4000 ms | wifi=on mqtt=on
```

Cửa sổ 2 (`mosquitto_sub`):
```text
traffic/inter1/light/status online
traffic/inter1/light/state {"device":"esp32-inter1","state":"GREEN","seq":1,"ms_in_state":4848,...,"reason":"connect"}
traffic/inter1/light/state {..."state":"GREEN",...,"reason":"heartbeat"}
traffic/inter1/light/state {..."state":"YELLOW","seq":2,"ms_in_state":0,...,"reason":"change"}
```

### 4.6. Checklist — "xong" khi tất cả đạt

- [ ] Verify không lỗi trong Arduino IDE.
- [ ] Đèn vẫn đúng chu kỳ như bước 1a, ngay cả **trước khi** Wi-Fi kết nối.
- [ ] `mosquitto_sub` nhận `status online` và `state` mỗi ~1 s.
- [ ] Mỗi lần LED đổi màu, có bản tin `reason":"change"` với `ms_in_state` gần 0 và `seq` tăng 1.
- [ ] **Tắt broker** (Ctrl+C cửa sổ 1): đèn **vẫn chạy**, Serial in `MQTT: that bai ... thu lai`. Bật lại → tự kết nối lại.
- [ ] **Rút nguồn ESP32**: sau khoảng 5–8 s, cửa sổ 2 nhận `traffic/inter1/light/status offline` (Last Will).
- [ ] Ghi lại: lúc tắt broker, có thấy đèn đổi màu trễ (>1 s) không? (xem Hạn chế).

---

## 5. Chạy trên Wokwi (không cần mạch, không cần broker trên laptop)

Wokwi mô phỏng Wi-Fi nhưng **không kết nối được tới laptop**, chỉ ra Internet. Có thể dùng broker công cộng để thử:

- `secrets.h` trên Wokwi: `WIFI_SSID "Wokwi-GUEST"`, `WIFI_PASSWORD ""`, `MQTT_HOST "test.mosquitto.org"`, `MQTT_USER ""`.
- Trong `config.h` đổi `MQTT_TOPIC_BASE` thành chuỗi riêng (ví dụ `"btl-nhom3-xyz/light"`) — broker công cộng **ai cũng đọc được**.
- Thêm thư viện PubSubClient trong tab **Library Manager** của Wokwi; tạo thêm file `config.h` và `secrets.h`.
- Trên laptop: `mosquitto_sub -h test.mosquitto.org -t "btl-nhom3-xyz/#" -v`.

Chỉ dùng cách này để thử logic, không gửi dữ liệu thật lên broker công cộng.

---

## 6. Lỗi thường gặp

| Hiện tượng | Nguyên nhân hay gặp |
|---|---|
| `PubSubClient.h: No such file or directory` dù đã cài | Sketchbook ở đường dẫn có dấu → mục 0.1 |
| Wi-Fi không bao giờ `da ket noi` | Mạng 5 GHz; sai mật khẩu; Wi-Fi trường cần đăng nhập web (captive portal) → dùng hotspot điện thoại 2,4 GHz |
| `rc=-2` | Sai `MQTT_HOST`; broker chưa chạy hoặc vẫn là service mặc định (chỉ localhost); firewall chặn; mạng có *client isolation* (Wi-Fi trường/công cộng thường chặn các thiết bị nói chuyện với nhau) |
| `rc=4` hoặc `rc=5` | Sai user/mật khẩu MQTT, hoặc chưa trỏ `password_file` đúng (phải chạy broker từ thư mục gốc dự án) |
| Broker báo `Address already in use` | Service `mosquitto` vẫn chạy → mục 3.1 |
| Kết nối được rồi mất liên tục | Hai ESP32 dùng trùng `DEVICE_ID` → broker đá nhau |

## 7. Hạn chế đã biết

- Khi broker không tới được, mỗi lần thử lại (5 s/lần) có thể chặn `loop()` tối đa khoảng 1,5 s
  (`MQTT_CONNECT_TIMEOUT_MS` + `MQTT_SOCKET_TIMEOUT_S`) → đèn có thể đổi màu trễ tương ứng. Khi đó laptop cũng không
  nhận được trạng thái nên sẽ ở `UNKNOWN`, không ảnh hưởng kết luận vi phạm. Nếu cần loại bỏ hẳn: tách mạng sang task FreeRTOS riêng (làm sau nếu thật sự cần).
- PubSubClient chỉ gửi QoS 0 (xem mục 2).
- Thời gian dựa trên đồng hồ laptop lúc nhận; sai số bằng độ trễ mạng LAN (thường vài chục ms).
