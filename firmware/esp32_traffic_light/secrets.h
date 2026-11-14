// secrets.example.h — MẪU. Copy thành secrets.h rồi điền thông tin thật.
// secrets.h đã nằm trong .gitignore — KHÔNG đưa lên Git.

#pragma once

#define WIFI_SSID     "Redmi"   // ESP32 chỉ hỗ trợ Wi-Fi 2,4 GHz
#define WIFI_PASSWORD "1234567@"  

// IPv4 của laptop trên mạng Hotspot Redmi
#define MQTT_HOST     "10.133.25.75"

// Tài khoản MQTT đã tạo trong tools/mosquitto/passwd
#define MQTT_USER     "esp32"
#define MQTT_PASSWORD "123"

