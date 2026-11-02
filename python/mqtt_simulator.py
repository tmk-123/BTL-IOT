"""Publish synthetic lamp heartbeats to the loopback test broker only."""

import argparse
import json
import time

import paho.mqtt.client as mqtt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=["RED", "GREEN", "YELLOW"], default="RED")
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error("--seconds must be within 1..3600")
    topic = "demo/inter1/light"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="lamp-demo")
    client.will_set(topic + "/status", "offline", qos=1, retain=True)
    try:
        client.connect("127.0.0.1", 18884, 5)
        client.loop_start()
        client.publish(topic + "/status", "online", qos=1, retain=True).wait_for_publish()
        started = time.monotonic()
        print(f"SIMULATION: {args.state} on loopback:18884, topic {topic}; no ESP32 involved")
        while time.monotonic() - started < args.seconds:
            age = int((time.monotonic() - started) * 1000)
            payload = dict(device="esp32-inter1", state=args.state, seq=1,
                           ms_in_state=age, duration_ms=(args.seconds + 2) * 1000,
                           uptime_ms=age, reason="heartbeat")
            client.publish(topic + "/state", json.dumps(payload)).wait_for_publish()
            time.sleep(0.5)
        client.publish(topic + "/status", "offline", qos=1, retain=True).wait_for_publish()
        return 0
    except OSError as exc:
        print(f"Cannot connect to local test broker: {exc}")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    raise SystemExit(main())
