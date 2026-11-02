"""Receive ESP32 lamp state using Paho MQTT, with reconnection and expiry."""

import argparse
import getpass
from math import isfinite
import os
import time
from uuid import uuid4

import paho.mqtt.client as mqtt

from light_state import LightState


class MqttLight:
    def __init__(self, host, port=1883, username=None, password=None,
                 topic="traffic/inter1/light", device="esp32-inter1", stale_after=1.5):
        self.state = LightState(stale_after, device)
        self.topic = topic.rstrip("/")
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"laptop-{uuid4().hex[:12]}")
        if username:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_connect_fail = self.on_connect_fail
        self.client.reconnect_delay_set(1, 10)
        self.host, self.port = host, port
        self.online = None

    def start(self):
        print(f"MQTT: connecting to {self.host}:{self.port}; waiting for fresh lamp data")
        self.client.connect_async(self.host, self.port, keepalive=5)
        self.client.loop_start()

    def stop(self):
        self.client.disconnect()
        self.client.loop_stop()
        self.state.unknown()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.online = None
        self.state.unknown()
        if reason_code.is_failure:
            print(f"MQTT: connection rejected ({reason_code}); light UNKNOWN")
            return
        client.subscribe([(self.topic + "/state", 0), (self.topic + "/status", 1)])
        print("MQTT: connected; subscribed to lamp state/status")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.online = False
        self.state.unknown()
        print("MQTT: disconnected; light UNKNOWN")

    def on_connect_fail(self, client, userdata):
        self.state.unknown()
        print("MQTT: cannot reach broker; retrying, light UNKNOWN")

    def on_message(self, client, userdata, message):
        if message.topic == self.topic + "/status":
            # Even retained online is not proof of a fresh color.
            self.online = message.payload == b"online"
            self.state.unknown()
        elif message.topic == self.topic + "/state":
            if self.online is False:
                return
            if not self.state.ingest(message.payload, retained=message.retain):
                print("MQTT: ignored invalid/retained/wrong-device state")


def add_mqtt_arguments(parser):
    parser.add_argument("--mqtt-host", help="Enable live lamp receiver (e.g. 127.0.0.1)")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-user", default=os.environ.get("MQTT_USER"))
    parser.add_argument("--mqtt-topic", default="traffic/inter1/light")
    parser.add_argument("--mqtt-device", default="esp32-inter1")
    parser.add_argument("--light-timeout", type=float, default=1.5)


def from_arguments(args):
    if not args.mqtt_host:
        return None
    password = os.environ.get("MQTT_PASSWORD")
    if args.mqtt_user and password is None:
        password = getpass.getpass("MQTT password (hidden): ")
    return MqttLight(args.mqtt_host, args.mqtt_port, args.mqtt_user, password,
                     args.mqtt_topic, args.mqtt_device, args.light_timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_mqtt_arguments(parser)
    args = parser.parse_args()
    if not args.mqtt_host:
        parser.error("Provide --mqtt-host")
    if not 1 <= args.mqtt_port <= 65535 or not isfinite(args.light_timeout) or args.light_timeout <= 0:
        parser.error("Require port 1..65535 and a positive finite light-timeout")
    receiver = from_arguments(args)
    try:
        receiver.start()
        previous = None
        while True:
            state = receiver.state.current()
            if state != previous:
                print(f"LIGHT: {state}")
                previous = state
            time.sleep(0.1)
    except KeyboardInterrupt:
        return 0
    finally:
        receiver.stop()


if __name__ == "__main__":
    raise SystemExit(main())
