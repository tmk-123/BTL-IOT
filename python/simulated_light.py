"""Own a loopback-only broker and publish clearly isolated simulated lamp states."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from uuid import uuid4

import paho.mqtt.client as mqtt


class SimulatedLight:
    def __init__(self, output, broker_exe=None):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.session = uuid4().hex[:12]
        self.topic = f'demo/{self.session}/light'
        self.device = f'simulation-{self.session}'
        self.state = 'GREEN'
        self.enabled = True
        self.seq = 1
        self.started = self.changed = time.monotonic()
        self.connected = False
        self.process = None
        self.client = None
        self.log = None
        broker = broker_exe or shutil.which('mosquitto') or 'C:/Program Files/mosquitto/mosquitto.exe'
        if not Path(broker).is_file():
            raise FileNotFoundError('Mosquitto was not found; install it before running this local demo')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        config = self.output / f'broker_{self.session}.conf'
        config.write_text(f'listener {self.port} 127.0.0.1\nallow_anonymous true\npersistence false\n', encoding='utf-8')
        try:
            self.log = (self.output / f'broker_{self.session}.log').open('w')
            self.process = subprocess.Popen([str(broker), '-c', str(config)], stdout=self.log, stderr=subprocess.STDOUT,
                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + 4
            while True:
                if self.process.poll() is not None:
                    raise OSError('The local demo broker could not start; inspect its log')
                try:
                    with socket.create_connection(('127.0.0.1', self.port), timeout=.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('The local demo broker did not start in time')
                    time.sleep(.05)
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f'demo-control-{self.session}')
            self.client.will_set(self.topic+'/status', 'offline', qos=1, retain=True)
            self.client.on_connect = self._connect
            self.client.on_disconnect = self._disconnect
            self.client.connect('127.0.0.1', self.port, keepalive=5)
            self.client.loop_start()
            while not self.connected:
                if time.monotonic() >= deadline:
                    raise TimeoutError('MQTT publisher did not connect')
                time.sleep(.02)
            self.publish('connect')
        except BaseException:
            self.close()
            raise

    def _connect(self, client, userdata, flags, reason_code, properties):
        self.connected = not reason_code.is_failure
        if self.connected:
            client.publish(self.topic+'/status', 'online', qos=1, retain=True)

    def _disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False

    def set_state(self, state):
        if state not in ('RED', 'GREEN', 'YELLOW', 'UNKNOWN'):
            raise ValueError('Unsupported simulated lamp state')
        if state == 'UNKNOWN':
            self.enabled = False  # Let the receiver's real heartbeat timeout expire.
            return
        self.state = state
        self.enabled = True
        self.seq += 1
        self.changed = time.monotonic()
        self.publish('change')

    def publish(self, reason='heartbeat'):
        if not self.enabled:
            return
        if not self.connected:
            raise ConnectionError('Demo MQTT broker disconnected')
        now = time.monotonic()
        payload = dict(device=self.device, state=self.state, seq=self.seq,
                       ms_in_state=int((now-self.changed)*1000), duration_ms=86400000,
                       uptime_ms=int((now-self.started)*1000), reason=reason, simulation=True)
        sent = self.client.publish(self.topic+'/state', json.dumps(payload), qos=1, retain=False)
        sent.wait_for_publish(timeout=1)
        if not sent.is_published():
            raise TimeoutError('Could not publish simulated lamp heartbeat')

    def close(self):
        if self.client is not None:
            try:
                if self.connected:
                    self.client.publish(self.topic+'/status', 'offline', qos=1, retain=True).wait_for_publish(timeout=1)
                self.client.disconnect()
            finally:
                self.client.loop_stop()
                self.client = None
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None
