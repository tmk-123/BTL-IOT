# Lý thuyết nền cho đề tài IoT giao thông

Tài liệu học cho cả nhóm. Đọc theo thứ tự; mỗi phần gắn với một giai đoạn của dự án.
Cuối tài liệu có câu hỏi tự kiểm tra.

| Phần | Dùng ở giai đoạn |
|---|---|
| 1. Mô hình IoT 4 lớp | Toàn dự án |
| 2. ESP32, GPIO, LED | GĐ 1 |
| 3. `millis()` và máy trạng thái | GĐ 1 |
| 4. Mạng cơ bản | GĐ 4 |
| 5. HTTP | GĐ 4 |
| 6. MQTT | GĐ 4 (phương án thay thế/nâng cấp) |
| 7. So sánh HTTP và MQTT | GĐ 4 |
| 8. Đồng bộ thời gian | GĐ 4 |
| 9. Detection, tracking, crossing, OCR | GĐ 2, 3, 5 |

---

## 1. Mô hình IoT 4 lớp

Một hệ IoT thường được chia thành 4 lớp. Đặt dự án vào khung này:

```text
┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│ 1. DEVICE       │──►│ 2. COMMUNICATION │──►│ 3. PROCESSING        │──►│ 4. APPLICATION   │
│ ESP32 + 3 LED   │   │ Wi-Fi + HTTP     │   │ Python trên laptop:  │   │ Web Streamlit:   │
│ Camera/video    │   │ (hoặc MQTT)      │   │ YOLO, tracking,      │   │ xem, lọc, thống  │
│                 │   │                  │   │ logic vi phạm, OCR,  │   │ kê vi phạm       │
│                 │   │                  │   │ SQLite               │   │                  │
└─────────────────┘   └──────────────────┘   └──────────────────────┘   └──────────────────┘
```

Ý nghĩa: mỗi lớp có thể thay thế độc lập. Ví dụ đổi HTTP sang MQTT chỉ ảnh hưởng lớp 2;
đổi Streamlit sang Flask chỉ ảnh hưởng lớp 4. Vì vậy nhóm phải **thống nhất định dạng dữ liệu
giữa các lớp** (xem `DECISIONS.md` và phần hợp đồng dữ liệu).

---

## 2. ESP32, GPIO và LED

**ESP32** là vi điều khiển (microcontroller) có sẵn Wi-Fi và Bluetooth, lập trình bằng C++ qua Arduino IDE.
Khác laptop: không có hệ điều hành đầy đủ, chạy **một** chương trình lặp vô hạn.

**GPIO** (General Purpose Input/Output) là các chân có thể:
- làm **output**: xuất mức điện áp HIGH (3,3 V) hoặc LOW (0 V) → bật/tắt LED;
- làm **input**: đọc nút bấm, cảm biến.

```cpp
pinMode(25, OUTPUT);     // khai báo chân 25 là output
digitalWrite(25, HIGH);  // xuất 3,3 V → LED sáng
digitalWrite(25, LOW);   // xuất 0 V   → LED tắt
```

**Vì sao cần điện trở?** LED gần như không tự giới hạn dòng. Nối thẳng 3,3 V vào LED → dòng rất lớn → hỏng LED
hoặc chân GPIO (mỗi chân ESP32 chỉ nên cấp khoảng ≤ 20 mA).

Tính điện trở theo định luật Ohm:

```text
R = (U_nguồn − U_LED) / I = (3,3 V − 2,0 V) / 0,006 A ≈ 217 Ω  → chọn 220 Ω
```

(U_LED đỏ/vàng ≈ 2 V, xanh lá có thể ≈ 2–3 V nên sáng yếu hơn — chấp nhận được, hoặc dùng 150 Ω cho LED xanh.)

**LED có cực:** chân dài = anode (+), chân ngắn = cathode (−, nối GND).

**Chân nên tránh trên ESP32:**
- GPIO 0, 2, 5, 12, 15: chân *strapping*, quyết định chế độ khởi động → nối LED có thể làm board không boot/nạp được.
- GPIO 34–39: chỉ đọc, không xuất được.
- GPIO 6–11: nối với bộ nhớ flash, không dùng.

Vì vậy dự án tạm chọn GPIO **25, 26, 27**.

---

## 3. `delay()` vs `millis()` và máy trạng thái

### Cách ngây thơ: `delay()`

```cpp
void loop() {
  bat(XANH); delay(10000);
  bat(VANG); delay(3000);
  bat(DO);   delay(10000);
}
```

Chạy được, nhưng trong 10 giây `delay()`, ESP32 **không làm được gì khác**: không trả lời HTTP,
không gửi MQTT, không đọc nút bấm. Ở GĐ 4 ESP32 phải vừa đổi đèn vừa trả lời laptop → `delay()` không dùng được.

### Cách đúng: `millis()` — "nhìn đồng hồ" thay vì "ngủ"

`millis()` trả về số mili giây từ lúc ESP32 khởi động. Ý tưởng: ghi lại thời điểm bắt đầu trạng thái,
mỗi vòng `loop()` kiểm tra "đã đủ thời gian chưa?". Nếu chưa → làm việc khác, vòng sau kiểm tra tiếp.

```cpp
if (millis() - stateStartedAt >= duration) {
  // đủ thời gian → chuyển trạng thái
}
// ... phần còn lại của loop() vẫn chạy liên tục (sau này: xử lý HTTP)
```

Ví von: `delay()` là đặt báo thức rồi đi ngủ; `millis()` là thỉnh thoảng nhìn đồng hồ trong lúc vẫn làm việc khác.

**Tràn số:** `millis()` là số 32-bit, quay về 0 sau ~49,7 ngày. Viết dạng `now - start >= duration`
(phép trừ số không dấu) vẫn đúng khi tràn; viết `now >= start + duration` thì **sai** khi tràn.

### Máy trạng thái hữu hạn (Finite State Machine — FSM)

Đèn giao thông là ví dụ kinh điển của FSM: có tập trạng thái hữu hạn và quy tắc chuyển.

```text
        10 s              3 s              10 s
GREEN ───────► YELLOW ───────► RED ───────► GREEN ...
```

Trong code:
- `enum LightState { GREEN, YELLOW, RED }` — tập trạng thái;
- `nextState()` — quy tắc chuyển;
- `stateDuration()` — thời gian ở mỗi trạng thái;
- `applyLights()` — "đầu ra" của mỗi trạng thái (LED nào sáng).

Lợi ích: thêm trạng thái mới (ví dụ chế độ nhấp nháy vàng ban đêm) chỉ cần thêm vào enum và các hàm trên.

---

## 4. Mạng cơ bản cần biết

| Khái niệm | Giải thích | Trong dự án |
|---|---|---|
| **LAN / Wi-Fi** | Mạng nội bộ; các thiết bị cùng router nói chuyện được với nhau | ESP32 và laptop phải **cùng một mạng Wi-Fi** |
| **Wi-Fi 2,4 GHz** | ESP32 **không** hỗ trợ 5 GHz | Phát hotspot điện thoại ở 2,4 GHz nếu Wi-Fi trường chặn |
| **Địa chỉ IP** | "Số nhà" của thiết bị, ví dụ `192.168.1.50` | ESP32 in IP ra Serial khi kết nối Wi-Fi |
| **Port** | "Số phòng" trong nhà — một máy chạy nhiều dịch vụ | HTTP mặc định port 80; MQTT port 1883 |
| **Client / Server** | Client gửi yêu cầu; server lắng nghe và trả lời | HTTP polling: laptop là client, ESP32 là server |
| **JSON** | Định dạng văn bản để trao đổi dữ liệu có cấu trúc | `{"state":"RED","seq":42}` |
| **Firewall** | Tường lửa chặn kết nối **đi vào** máy | Windows Firewall hay chặn kết nối vào laptop → lý do chọn laptop chủ động hỏi ESP32 |

---

## 5. HTTP

HTTP là giao thức của web: **client gửi request → server trả response**. Mỗi lần hỏi là một lượt riêng.

```text
Laptop (client)                         ESP32 (server, IP 192.168.1.50)
     │   GET /state HTTP/1.1                    │
     │ ───────────────────────────────────────► │
     │                                          │  đọc trạng thái hiện tại
     │   HTTP/1.1 200 OK                        │
     │   {"state":"RED","seq":42,               │
     │    "ms_in_state":1830}                   │
     │ ◄─────────────────────────────────────── │
```

- **Method**: `GET` (lấy dữ liệu), `POST` (gửi dữ liệu lên).
- **Status code**: `200` OK, `404` không có đường dẫn, `500` lỗi server.
- **Không có trạng thái (stateless)**: server không "nhớ" client giữa các lần hỏi.

### Polling và push

- **Polling (hỏi định kỳ)**: laptop hỏi ESP32 mỗi 200 ms "đèn đang màu gì?". Đơn giản; độ trễ tối đa ≈ chu kỳ hỏi.
- **Push (đẩy)**: ESP32 chủ động `POST` lên laptop mỗi khi đổi đèn. Nhanh hơn nhưng laptop phải chạy server
  (dễ vướng firewall), ESP32 phải biết IP laptop.

Thử HTTP không cần code: mở trình duyệt gõ `http://192.168.1.50/state` → thấy JSON. Hoặc trong terminal:

```bash
curl http://192.168.1.50/state
```

Python (thư viện `requests`):

```python
import requests
r = requests.get("http://192.168.1.50/state", timeout=0.5)
print(r.json()["state"])
```

---

## 6. MQTT

### 6.1. Ý tưởng: publish / subscribe qua "bưu điện"

Trong HTTP, hai bên nói chuyện **trực tiếp** và phải biết địa chỉ của nhau.
MQTT thêm một bên trung gian gọi là **broker**:

- Bên gửi **publish** (đăng) tin nhắn lên một **topic** (chủ đề) tại broker.
- Bên nhận **subscribe** (đăng ký theo dõi) topic đó.
- Broker chuyển tin cho **mọi** bên đã subscribe topic.

```text
                          ┌──────────────────────┐
  ESP32  ── publish ────► │       BROKER         │ ──── deliver ───► Python xử lý video
  topic:                  │  (Mosquitto, chạy    │ ──── deliver ───► Web dashboard
  traffic/inter1/light    │   trên laptop)       │ ──── deliver ───► (bất kỳ ai subscribe)
  "RED"                   └──────────────────────┘
```

Ví von: **YouTube**. Người đăng video (publisher) không cần biết ai xem; người xem (subscriber) bấm
"đăng ký" kênh (topic); YouTube (broker) lo gửi thông báo cho tất cả người đăng ký.
Còn HTTP giống **gọi điện**: phải biết số, hỏi gì đáp nấy, cúp máy là hết.

Hệ quả quan trọng: **publisher và subscriber không cần biết nhau**. ESP32 chỉ cần biết địa chỉ broker.
Thêm bên nhận mới (ví dụ web dashboard) không phải sửa firmware ESP32.

### 6.2. Topic

Topic là chuỗi phân cấp bằng dấu `/`, giống đường dẫn thư mục:

```text
traffic/inter1/light/state        ← trạng thái đèn nút giao 1
traffic/inter1/light/status       ← ESP32 online/offline
traffic/inter2/light/state        ← nút giao 2 (mở rộng sau)
```

Ký tự đại diện khi **subscribe**:
- `+` thay **một** cấp: `traffic/+/light/state` → nhận trạng thái đèn của mọi nút giao.
- `#` thay **mọi cấp còn lại**: `traffic/#` → nhận tất cả.

### 6.3. QoS — mức bảo đảm giao tin

| QoS | Ý nghĩa | Ví von |
|---|---|---|
| 0 | Gửi tối đa 1 lần, có thể mất | Thư thường |
| 1 | Ít nhất 1 lần, có thể **trùng** | Thư bảo đảm, có thể gửi lại |
| 2 | Đúng 1 lần | Thư bảo đảm + xác nhận 2 chiều; chậm nhất |

Với trạng thái đèn: QoS 0 hoặc 1 đều được. Thư viện PubSubClient trên ESP32 chỉ **gửi** được QoS 0; bù lại ESP32 gửi heartbeat mỗi 1 s và có `seq` để phát hiện mất tin.

### 6.4. Retained message và Last Will — rất hợp với bài toán

- **Retained (giữ lại)**: broker nhớ tin **cuối cùng** của topic. Ai subscribe sau sẽ nhận ngay tin đó.
  → Python khởi động giữa chừng vẫn biết ngay ESP32 đang `online` hay `offline`.
  Dự án **không** retain topic `state`: tin retained có thể đã cũ từ lâu nên `ms_in_state` trong đó không còn đúng.
  Thay vào đó ESP32 gửi heartbeat mỗi 1 s, nên Python chờ tối đa 1 s là có trạng thái mới.
- **Last Will and Testament (LWT, "di chúc")**: khi kết nối, ESP32 gửi trước cho broker một tin
  "nếu tôi mất kết nối bất thường, hãy publish `offline` lên `traffic/inter1/light/status`".
  ESP32 mất điện/mất Wi-Fi → broker tự publish tin đó → Python chuyển sang **`UNKNOWN`** ngay.
- **Keep-alive**: client định kỳ "ping" broker; quá thời gian không ping → broker coi là mất kết nối và kích hoạt LWT.

### 6.5. Thử MQTT không cần ESP32

Cài **Mosquitto** (broker mã nguồn mở) trên Windows từ https://mosquitto.org/download/ — gồm broker
`mosquitto` và hai công cụ `mosquitto_sub`, `mosquitto_pub`. Mở 3 cửa sổ terminal trong thư mục cài Mosquitto:

```bash
# Cửa sổ 1 — chạy broker, -v để in log
mosquitto -v

# Cửa sổ 2 — subscribe tất cả topic traffic
mosquitto_sub -h localhost -t "traffic/#" -v

# Cửa sổ 3 — giả làm ESP32, publish trạng thái (retained)
mosquitto_pub -h localhost -t "traffic/inter1/light/state" -m '{"state":"RED","seq":1}' -r
```

Cửa sổ 2 sẽ in tin vừa publish. Tắt cửa sổ 2, mở lại → vẫn nhận ngay tin cũ nhờ `-r` (retained).

Phía Python (thư viện `paho-mqtt`, máy đã cài bản 2.1.0):

```python
import json
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    print(msg.topic, data["state"])

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.username_pw_set("laptop", "<mat_khau>")   # broker của dự án bắt buộc đăng nhập
client.connect("localhost", 1883)
client.subscribe("traffic/inter1/light/state", qos=1)
client.loop_forever()
```

Phía ESP32 thường dùng thư viện **PubSubClient** (cài qua Library Manager của Arduino IDE).

### 6.6. Lưu ý bảo mật

Mosquitto bản mới mặc định chỉ cho kết nối từ chính máy đó. Muốn ESP32 kết nối vào cần cấu hình
`listener 1883` và cho phép (hoặc tạo user/password); đồng thời mở port 1883 trên Windows Firewall.
Đây chính là phần "phức tạp hơn" khiến dự án đề xuất HTTP trước.

---

## 7. So sánh HTTP và MQTT trong dự án này

| Tiêu chí | HTTP polling | MQTT |
|---|---|---|
| Cài thêm | Không | Broker Mosquitto |
| Debug | Mở trình duyệt là thấy | Cần `mosquitto_sub` hoặc MQTT Explorer |
| Firewall Windows | Không cần mở port (laptop gọi ra) | Phải mở port 1883 cho ESP32 kết nối vào |
| Độ trễ báo đổi đèn | ≤ chu kỳ hỏi (~200 ms) | Gần như tức thì |
| Phát hiện ESP32 mất kết nối | Request lỗi/timeout | LWT tự động |
| Nhiều bên nhận | Mỗi bên tự hỏi ESP32 | Broker phát cho tất cả |
| "Đúng chất IoT" | Trung bình | Cao — giao thức IoT tiêu chuẩn |

Kết luận đề xuất (`DECISIONS.md` D-01): **HTTP trước** để có luồng chạy được sớm; chuyển MQTT nếu giảng viên
yêu cầu hoặc khi cần nhiều bên nhận. Phía Python tách riêng lớp "nguồn trạng thái đèn" nên đổi giao thức chỉ sửa một module.

---

## 8. Đồng bộ thời gian — vì sao quan trọng

Câu hỏi cốt lõi: *"Lúc xe chạm vạch, đèn màu gì?"* Hai sự kiện đến từ hai nơi:
- thời điểm xe qua vạch: Python tính từ video, theo **đồng hồ laptop**;
- thời điểm đèn đổi: ESP32 biết, theo `millis()` của **ESP32** (bắt đầu từ 0 khi bật nguồn — không phải giờ thật).

Hai đồng hồ khác nhau → phải quy về một chuẩn. Dự án chọn **đồng hồ laptop làm chuẩn**:

```text
ESP32 trả: {"state":"RED", "ms_in_state":1830}
Laptop nhận lúc 19:05:03.500
→ Đèn đỏ bắt đầu lúc 19:05:03.500 − 1,830 s = 19:05:01.670 (giờ laptop)
```

Sai số ≈ độ trễ mạng LAN (thường vài chục ms) — đủ tốt cho demo.

**Trạng thái hết hạn → `UNKNOWN`:** nếu quá 1,5 s không nhận được cập nhật, Python **không** giả định đèn vẫn đỏ
mà đánh dấu `UNKNOWN`; sự kiện crossing lúc đó được ghi `UNVERIFIED`, không kết luận vi phạm.

**Vùng biên:** xe qua vạch đúng lúc đèn vừa chuyển đỏ (vài trăm ms) là vùng không chắc chắn do sai số.
Có thể cấu hình một khoảng "ân hạn" (grace period) sau khi chuyển đỏ.

---

## 9. Pipeline AI — khái niệm (chi tiết sẽ bổ sung ở GĐ 2, 3, 5)

| Bước | Câu hỏi trả lời | Kết quả |
|---|---|---|
| **Detection** (YOLO) | Frame này có xe nào, ở đâu? | Hộp bao (bounding box), loại xe, độ tin cậy. Mỗi frame độc lập |
| **Tracking** (ByteTrack) | Xe ở frame này có phải xe ở frame trước? | `track_id` không đổi qua nhiều frame |
| **Crossing line** | Xe có đi **qua** vạch, lúc nào? | Một sự kiện duy nhất cho mỗi `track_id` |
| **Phát hiện biển số** | Biển số nằm đâu trong ảnh xe? | Ảnh cắt vùng biển số |
| **OCR** | Ảnh biển số ghi chữ gì? | Chuỗi ký tự + độ tin cậy (có thể sai) |

**Vì sao cần tracking?** Detection chỉ nói "có một xe ở đây" từng frame. Không có tracking thì một xe đi qua
30 frame sẽ bị đếm thành 30 sự kiện.

**Kiểm tra xe ở phía nào của vạch** — dùng tích có hướng (cross product). Vạch đi từ A đến B, điểm P là giữa
cạnh đáy bounding box (nơi bánh xe chạm đường):

```text
d = (B.x − A.x)·(P.y − A.y) − (B.y − A.y)·(P.x − A.x)
d > 0 → P ở một phía;  d < 0 → phía còn lại;  d = 0 → nằm trên vạch
```

Xe **vượt vạch** khi dấu của `d` (của cùng `track_id`) đổi từ phía "trước vạch" sang "sau vạch"
và giữ ổn định vài frame (chống rung bounding box).

**Vi phạm** = có sự kiện crossing **và** trạng thái đèn tại thời điểm đó là `RED` **và** trạng thái không bị hết hạn.

---

## Câu hỏi tự kiểm tra

1. Vì sao không dùng `delay()` cho đèn giao thông khi ESP32 còn phải trả lời laptop?
2. Vì sao viết `now - start >= duration` an toàn hơn `now >= start + duration`?
3. Tính điện trở cho LED 2 V, dòng 8 mA, nguồn 3,3 V.
4. Vì sao không nối LED vào GPIO 2 hoặc 12?
5. Trong MQTT, ESP32 có cần biết IP của laptop chạy Python không? Cần biết IP của ai?
6. Retained message giúp gì khi chương trình Python khởi động lại?
7. Last Will giúp chuyển trạng thái sang `UNKNOWN` như thế nào?
8. Vì sao xe đứng gần vạch khi đèn đỏ chưa chắc là vi phạm?
9. Vì sao không thể so trực tiếp `millis()` của ESP32 với giờ trên laptop?
10. Khi nào nên đổi từ HTTP sang MQTT?
