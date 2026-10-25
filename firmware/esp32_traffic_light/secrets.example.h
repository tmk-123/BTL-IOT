// secrets.example.h — MẪU. Copy thành secrets.h rồi điền thông tin thật.
// secrets.h đã nằm trong .gitignore — KHÔNG đưa lên Git.

#pragma once

#define WIFI_SSID     "TEN_WIFI_2_4GHZ"   // ESP32 chỉ hỗ trợ Wi-Fi 2,4 GHz
#define WIFI_PASSWORD "MAT_KHAU_WIFI"

// IPv4 của laptop chạy Mosquitto (lệnh `ipconfig`, mục "Wireless LAN adapter Wi-Fi")
#define MQTT_HOST     "192.168.1.100"

// Tài khoản MQTT tạo bằng mosquitto_passwd. Để chuỗi rỗng "" nếu broker cho phép ẩn danh.
#define MQTT_USER     "esp32"
#define MQTT_PASSWORD "DOI_MAT_KHAU_NAY"
