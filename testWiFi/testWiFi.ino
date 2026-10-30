#include <WiFi.h>

const char *ssid = "Redmi";
const char *password = "1234567@";

const char *statusName(wl_status_t status) {
  switch (status) {
    case WL_CONNECTED: return "CONNECTED";
    case WL_NO_SSID_AVAIL: return "NO_SSID_AVAILABLE";
    case WL_CONNECT_FAILED: return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED: return "DISCONNECTED";
    case WL_IDLE_STATUS: return "IDLE";
    default: return "OTHER";
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n=== TEST WIFI ESP32-CAM ===");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(300);

  Serial.println("Scanning 2.4 GHz networks...");
  int count = WiFi.scanNetworks();
  bool targetFound = false;
  if (count < 0) Serial.println("Scan failed. Press RST to retry.");
  if (count == 0) Serial.println("No networks found.");
  for (int i = 0; i < count; i++) {
    bool isTarget = WiFi.SSID(i) == ssid;
    if (isTarget) targetFound = true;
    Serial.printf("%2d | %s | RSSI %d dBm | CH %d%s\n",
                  i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i),
                  WiFi.channel(i), isTarget ? " | TARGET" : "");
  }
  WiFi.scanDelete();
  Serial.printf("Configured SSID: %s\n", ssid);
  Serial.println(targetFound ? "Target found in scan." :
    "Target not found: check SSID, 2.4 GHz, range or hidden SSID.");

  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  Serial.println("Connecting (up to 30 seconds)...");
  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 30000) {
    Serial.printf("Status: %s\n", statusName(WiFi.status()));
    delay(1000);
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("SUCCESS: WiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    Serial.printf("Signal: %d dBm\n", WiFi.RSSI());
    Serial.println("This sketch tests WiFi only; no camera web page.");
  } else {
    Serial.printf("FAILED: %s\n", statusName(WiFi.status()));
    Serial.println("Check password and router settings; try a 2.4 GHz phone hotspot.");
  }
}

void loop() {
  delay(10000);
}