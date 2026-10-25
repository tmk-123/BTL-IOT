// led_test.ino — Test phần cứng: kiểm tra 3 LED đèn giao thông đã đấu đúng chưa.
// KHÔNG dùng Wi-Fi/MQTT. Nạp sketch này trước, đạt rồi mới nạp esp32_traffic_light.
//
// Chạy 2 pha, lặp lại mãi:
//   Pha 1: bật lần lượt TỪNG LED 1 giây (ĐỎ -> VÀNG -> XANH) để kiểm tra từng dây.
//   Pha 2: chu kỳ đèn giao thông rút gọn XANH 3 s -> VÀNG 1 s -> ĐỎ 3 s.
// Serial Monitor (115200) in ra LED nào đang được bật để đối chiếu với mạch thật.

// Chân GPIO giống firmware chính (config.h). Đổi chân thì sửa cả hai nơi.
const int PIN_RED    = 25;
const int PIN_YELLOW = 26;
const int PIN_GREEN  = 27;

// 1 = GPIO -> điện trở -> chân dài LED, chân ngắn -> GND (ghi HIGH để bật).
//     Module đèn giao thông 4 chân (R, Y, G, GND) cũng dùng 1.
// 0 = LED nối ngược (anode lên 3V3), ghi LOW để bật.
#define LED_ACTIVE_HIGH 1

void setLed(int pin, bool on) {
  digitalWrite(pin, (on == (LED_ACTIVE_HIGH == 1)) ? HIGH : LOW);
}

void showOnly(int pinOn, const char* name, unsigned long ms) {
  setLed(PIN_RED,    pinOn == PIN_RED);
  setLed(PIN_YELLOW, pinOn == PIN_YELLOW);
  setLed(PIN_GREEN,  pinOn == PIN_GREEN);
  Serial.printf("[t=%lu ms] BAT %s (GPIO %d) trong %lu ms\n", millis(), name, pinOn, ms);
  delay(ms);  // dùng delay() cho đơn giản; firmware chính dùng millis()
}

void setup() {
  Serial.begin(115200);
  delay(200);
  pinMode(PIN_RED, OUTPUT);
  pinMode(PIN_YELLOW, OUTPUT);
  pinMode(PIN_GREEN, OUTPUT);
  Serial.println();
  Serial.println("=== LED TEST: kiem tra dau day 3 LED ===");
  Serial.printf("GPIO: RED=%d YELLOW=%d GREEN=%d\n", PIN_RED, PIN_YELLOW, PIN_GREEN);
}

void loop() {
  Serial.println("--- Pha 1: tung LED ---");
  showOnly(PIN_RED,    "DO",   1000);
  showOnly(PIN_YELLOW, "VANG", 1000);
  showOnly(PIN_GREEN,  "XANH", 1000);

  Serial.println("--- Pha 2: chu ky den giao thong rut gon ---");
  showOnly(PIN_GREEN,  "XANH", 3000);
  showOnly(PIN_YELLOW, "VANG", 1000);
  showOnly(PIN_RED,    "DO",   3000);
}
