// config.h — Cấu hình đèn giao thông ESP32
// Muốn đổi chân GPIO, thời gian đèn hoặc topic MQTT: chỉ sửa file này.
// Thông tin bí mật (Wi-Fi, IP broker, mật khẩu MQTT) nằm trong secrets.h.

#pragma once

// ----- Chân GPIO nối LED (ESP32 DevKit) -----
// Giả định ban đầu, chưa chốt với nhóm. Tránh các chân strapping (0, 2, 5, 12, 15)
// và chân chỉ-đọc (34–39).
#define PIN_LED_RED     25
#define PIN_LED_YELLOW  26
#define PIN_LED_GREEN   27

// 1 = nối GPIO -> điện trở -> chân dài LED (anode), chân ngắn (cathode) -> GND.
//     Ghi HIGH để bật LED (cách đấu khuyến nghị).
// 0 = LED nối ngược (anode lên 3V3, cathode về GPIO): ghi LOW để bật.
#define LED_ACTIVE_HIGH 1

// ----- Thời gian mỗi trạng thái (mili giây) -----
#define DURATION_GREEN_MS   10000UL
#define DURATION_YELLOW_MS   3000UL
#define DURATION_RED_MS     10000UL

// ----- Serial Monitor -----
#define SERIAL_BAUD 115200

// In dòng "còn lại bao lâu" theo chu kỳ này (ms). Đặt 0 để tắt, chỉ in khi đổi đèn.
#define STATUS_PRINT_INTERVAL_MS 1000UL

// ----- MQTT -----
#define DEVICE_ID   "esp32-inter1"           // client id, phải khác nhau giữa các ESP32
#define MQTT_PORT   1883
#define MQTT_TOPIC_BASE "traffic/inter1/light"
// Topic thực tế:
//   traffic/inter1/light/state   JSON trạng thái đèn (khi đổi đèn + heartbeat)
//   traffic/inter1/light/status  "online" / "offline" (retained, "offline" là Last Will)

#define HEARTBEAT_INTERVAL_MS    1000UL  // gửi lại trạng thái hiện tại định kỳ
#define MQTT_KEEPALIVE_S         5       // broker coi là mất kết nối sau ~1,5 x giá trị này
#define MQTT_RETRY_INTERVAL_MS   5000UL  // khoảng cách giữa các lần thử kết nối lại broker
#define MQTT_CONNECT_TIMEOUT_MS   500    // chờ mở kết nối TCP tối đa (mạng LAN: 500 ms là đủ)
#define MQTT_SOCKET_TIMEOUT_S       1    // chờ broker trả lời CONNACK tối đa
