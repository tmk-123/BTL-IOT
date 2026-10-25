// esp32_traffic_light.ino — Giai đoạn 1, bước 1b
// Điều khiển 3 LED theo chu kỳ XANH -> VÀNG -> ĐỎ -> XANH ...
// và gửi trạng thái đèn lên MQTT broker (Mosquitto trên laptop).
//
// Nguyên tắc: đèn KHÔNG phụ thuộc mạng. Mất Wi-Fi/broker thì đèn vẫn chạy,
// ESP32 tự thử kết nối lại; phía laptop nhận Last Will "offline" -> UNKNOWN.
// Không dùng delay() trong loop(): dùng millis() để loop() luôn chạy liên tục.
//
// Thư viện cần cài (Library Manager): PubSubClient (Nick O'Leary).

#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"
#include "secrets.h"   // copy từ secrets.example.h

enum LightState { GREEN, YELLOW, RED };

LightState currentState = GREEN;
unsigned long stateStartedAt = 0;   // millis() lúc vào trạng thái hiện tại
unsigned long lastStatusPrintAt = 0;
unsigned long seq = 0;              // đếm số lần đổi đèn, phía laptop dùng để phát hiện mất bản tin

WiFiClient netClient;
PubSubClient mqtt(netClient);
const char* TOPIC_STATE  = MQTT_TOPIC_BASE "/state";
const char* TOPIC_STATUS = MQTT_TOPIC_BASE "/status";
bool wifiWasConnected = false;
unsigned long lastMqttAttemptAt = 0;
unsigned long lastHeartbeatAt = 0;

const char* stateName(LightState s) {
  switch (s) {
    case GREEN:  return "GREEN";
    case YELLOW: return "YELLOW";
    case RED:    return "RED";
  }
  return "UNKNOWN";
}

unsigned long stateDuration(LightState s) {
  switch (s) {
    case GREEN:  return DURATION_GREEN_MS;
    case YELLOW: return DURATION_YELLOW_MS;
    case RED:    return DURATION_RED_MS;
  }
  return DURATION_RED_MS;
}

LightState nextState(LightState s) {
  switch (s) {
    case GREEN:  return YELLOW;
    case YELLOW: return RED;
    case RED:    return GREEN;
  }
  return RED;
}

void writeLed(int pin, bool on) {
  digitalWrite(pin, (on == (LED_ACTIVE_HIGH == 1)) ? HIGH : LOW);
}

// Luôn ghi cả 3 LED để bảo đảm chỉ có đúng một đèn sáng.
void applyLights(LightState s) {
  writeLed(PIN_LED_RED,    s == RED);
  writeLed(PIN_LED_YELLOW, s == YELLOW);
  writeLed(PIN_LED_GREEN,  s == GREEN);
}

// ---------------- MQTT ----------------

// Gửi trạng thái hiện tại. reason: "change" (vừa đổi đèn), "heartbeat" (định kỳ),
// "connect" (vừa kết nối broker). Không retained: người nhận dựa vào heartbeat.
void publishState(const char* reason, unsigned long now) {
  if (!mqtt.connected()) return;

  char payload[220];
  snprintf(payload, sizeof(payload),
           "{\"device\":\"%s\",\"state\":\"%s\",\"seq\":%lu,\"ms_in_state\":%lu,"
           "\"duration_ms\":%lu,\"uptime_ms\":%lu,\"reason\":\"%s\"}",
           DEVICE_ID, stateName(currentState), seq, now - stateStartedAt,
           stateDuration(currentState), now, reason);

  if (mqtt.publish(TOPIC_STATE, payload, false)) {
    lastHeartbeatAt = now;
  } else {
    Serial.printf("[t=%lu ms] MQTT publish THAT BAI (%s)\n", now, reason);
  }
}

void connectMqtt() {
  Serial.printf("[t=%lu ms] MQTT: ket noi %s:%d ...\n", millis(), MQTT_HOST, MQTT_PORT);

  // Last Will: nếu ESP32 mất kết nối bất thường, broker tự publish "offline" (retained).
  bool ok;
  if (strlen(MQTT_USER) > 0) {
    ok = mqtt.connect(DEVICE_ID, MQTT_USER, MQTT_PASSWORD, TOPIC_STATUS, 1, true, "offline");
  } else {
    ok = mqtt.connect(DEVICE_ID, TOPIC_STATUS, 1, true, "offline");
  }

  if (ok) {
    Serial.printf("[t=%lu ms] MQTT: da ket noi\n", millis());
    mqtt.publish(TOPIC_STATUS, "online", true);
    publishState("connect", millis());
  } else {
    // rc: -4 timeout, -2 khong mo duoc TCP (sai IP/firewall/broker tat),
    //      4 sai user/password, 5 khong duoc phep
    Serial.printf("[t=%lu ms] MQTT: that bai rc=%d, thu lai sau %lu ms\n",
                  millis(), mqtt.state(), MQTT_RETRY_INTERVAL_MS);
  }
}

// Gọi mỗi vòng loop(): theo dõi Wi-Fi, thử lại MQTT theo chu kỳ, xử lý keep-alive.
void maintainNetwork(unsigned long now) {
  bool wifiUp = (WiFi.status() == WL_CONNECTED);
  if (wifiUp != wifiWasConnected) {
    wifiWasConnected = wifiUp;
    if (wifiUp) {
      Serial.printf("[t=%lu ms] WiFi: da ket noi, IP ESP32 = %s\n",
                    now, WiFi.localIP().toString().c_str());
    } else {
      Serial.printf("[t=%lu ms] WiFi: mat ket noi, dang tu ket noi lai...\n", now);
    }
  }
  if (!wifiUp) return;

  if (!mqtt.connected()) {
    if (now - lastMqttAttemptAt >= MQTT_RETRY_INTERVAL_MS) {
      lastMqttAttemptAt = now;
      connectMqtt();
    }
    return;
  }

  mqtt.loop();  // gửi PINGREQ keep-alive, nhận gói tin từ broker

  if (now - lastHeartbeatAt >= HEARTBEAT_INTERVAL_MS) {
    publishState("heartbeat", now);
  }
}

// ---------------- Đèn ----------------

void enterState(LightState s, unsigned long now) {
  currentState = s;
  stateStartedAt = now;
  lastStatusPrintAt = now;
  seq++;
  applyLights(s);  // đổi đèn trước, rồi mới gửi mạng

  Serial.printf("[t=%lu ms] seq=%lu state=%s duration=%lu ms\n",
                now, seq, stateName(s), stateDuration(s));
  publishState("change", now);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(200);  // chờ Serial ổn định; chỉ chạy một lần khi khởi động

  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);

  Serial.println();
  Serial.println("=== ESP32 Traffic Light - buoc 1b (Wi-Fi + MQTT) ===");
  Serial.printf("GPIO: RED=%d YELLOW=%d GREEN=%d | active %s\n",
                PIN_LED_RED, PIN_LED_YELLOW, PIN_LED_GREEN,
                LED_ACTIVE_HIGH ? "HIGH" : "LOW");
  Serial.printf("Chu ky: GREEN %lu ms -> YELLOW %lu ms -> RED %lu ms\n",
                DURATION_GREEN_MS, DURATION_YELLOW_MS, DURATION_RED_MS);
  Serial.printf("WiFi SSID: %s | MQTT: %s:%d | topic: %s\n",
                WIFI_SSID, MQTT_HOST, MQTT_PORT, TOPIC_STATE);

  // Wi-Fi: begin() không chặn; đèn bắt đầu chạy ngay, kết nối hoàn tất sau.
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Giới hạn thời gian chờ để lúc broker không tới được, loop() bị chặn ít nhất có thể.
  netClient.setConnectionTimeout(MQTT_CONNECT_TIMEOUT_MS);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
  mqtt.setSocketTimeout(MQTT_SOCKET_TIMEOUT_S);

  enterState(GREEN, millis());
}

void loop() {
  unsigned long now = millis();
  // Phép trừ unsigned vẫn đúng khi millis() tràn số (sau ~49 ngày).
  unsigned long elapsed = now - stateStartedAt;

  if (elapsed >= stateDuration(currentState)) {
    enterState(nextState(currentState), now);
  } else if (STATUS_PRINT_INTERVAL_MS > 0 && now - lastStatusPrintAt >= STATUS_PRINT_INTERVAL_MS) {
    lastStatusPrintAt = now;
    unsigned long remaining = stateDuration(currentState) - elapsed;
    Serial.printf("[t=%lu ms] state=%s ms_in_state=%lu remaining=%lu ms | wifi=%s mqtt=%s\n",
                  now, stateName(currentState), elapsed, remaining,
                  WiFi.status() == WL_CONNECTED ? "on" : "off",
                  mqtt.connected() ? "on" : "off");
  }

  maintainNetwork(millis());
}
