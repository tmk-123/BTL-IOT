"""Real loopback MQTT test; launches and cleans up its own Mosquitto process."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
import paho.mqtt.client as mqtt
from mqtt_light import MqttLight
from light_state import classify_crossing

BROKER = os.environ.get("MOSQUITTO_EXE") or shutil.which("mosquitto")
if not BROKER and Path("C:/Program Files/mosquitto/mosquitto.exe").is_file():
    BROKER = "C:/Program Files/mosquitto/mosquitto.exe"


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for MQTT condition")


@unittest.skipUnless(BROKER, "Mosquitto executable is not installed")
class MqttIntegrationTests(unittest.TestCase):
    def test_real_broker_colors_expiry_retained_offline_and_disconnect(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "test.conf"
            config.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n")
            process = subprocess.Popen([BROKER, "-c", str(config)], stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            receiver = MqttLight("127.0.0.1", port, topic="integration/light", stale_after=0.5)
            publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            subscribed = threading.Event()
            receiver.client.on_subscribe = lambda *args: subscribed.set()
            try:
                def ready():
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                            return True
                    except OSError:
                        return False
                wait_for(ready)
                publisher.connect("127.0.0.1", port, 5)
                publisher.loop_start()
                # Retained RED must not restore a color when a new receiver subscribes.
                payload = dict(device="esp32-inter1", state="RED", seq=1, ms_in_state=100,
                               duration_ms=10000, uptime_ms=1000, reason="heartbeat")
                publisher.publish("integration/light/state", json.dumps(payload), qos=1, retain=True).wait_for_publish()
                receiver.start()
                self.assertTrue(subscribed.wait(5))
                time.sleep(0.1)
                self.assertEqual(receiver.state.current(), "UNKNOWN")
                for seq, color in enumerate(("RED", "GREEN", "YELLOW"), 2):
                    payload.update(state=color, seq=seq, uptime_ms=seq * 1000, ms_in_state=0)
                    publisher.publish("integration/light/state", json.dumps(payload), qos=1).wait_for_publish()
                    wait_for(lambda: receiver.state.current() == color)
                    now = time.monotonic()
                    assessment = classify_crossing(receiver.state, now, now)[1]
                    self.assertEqual(assessment, "suspected_red_light" if color == "RED" else "no_red_light_evidence")
                wait_for(lambda: receiver.state.current() == "UNKNOWN", timeout=2)
                payload.update(state="RED", seq=5, uptime_ms=5000)
                publisher.publish("integration/light/state", json.dumps(payload), qos=1).wait_for_publish()
                wait_for(lambda: receiver.state.current() == "RED")
                publisher.publish("integration/light/status", "offline", qos=1).wait_for_publish()
                wait_for(lambda: receiver.state.current() == "UNKNOWN")
                payload.update(uptime_ms=5100, ms_in_state=100)
                publisher.publish("integration/light/state", json.dumps(payload), qos=1).wait_for_publish()
                time.sleep(0.05)
                self.assertEqual(receiver.state.current(), "UNKNOWN")
                publisher.publish("integration/light/status", "online", qos=1).wait_for_publish()
                publisher.publish("integration/light/state", json.dumps(payload), qos=1).wait_for_publish()
                wait_for(lambda: receiver.state.current() == "RED")
                process.terminate()
                process.wait(timeout=5)
                wait_for(lambda: receiver.state.current() == "UNKNOWN")
                subscribed.clear()
                process = subprocess.Popen([BROKER, "-c", str(config)], stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL,
                                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                self.assertTrue(subscribed.wait(8), "Receiver did not reconnect and resubscribe")
                wait_for(publisher.is_connected, timeout=8)
                self.assertEqual(receiver.state.current(), "UNKNOWN")
                payload.update(uptime_ms=6000, ms_in_state=1000)
                publisher.publish("integration/light/status", "online", qos=1).wait_for_publish()
                publisher.publish("integration/light/state", json.dumps(payload), qos=1).wait_for_publish()
                wait_for(lambda: receiver.state.current() == "RED")
                print("PASS: real MQTT colors, retained rejection, expiry, offline, disconnect and reconnect")
            finally:
                receiver.stop()
                publisher.disconnect()
                publisher.loop_stop()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
