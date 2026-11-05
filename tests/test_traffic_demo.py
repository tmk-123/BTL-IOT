from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from traffic_demo import camera_command
from simulated_light import SimulatedLight
from mqtt_light import MqttLight


class DemoCommandTests(unittest.TestCase):
    def test_camera_command_isolated_and_marked_simulation(self):
        output = Path('data/demos/live_simulation')
        args = camera_command('http://192.168.1.25/', output, 12345, 'demo/session/light', 'simulation-session')
        self.assertEqual(args[args.index('--source')+1], 'http://192.168.1.25/capture')
        for flag in ('--simulation', '--select-line', '--track', '--save-all-evidence', '--plate-ocr'):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index('--database')+1], str(output/'traffic.db'))
        self.assertEqual(args[args.index('--mqtt-host')+1], '127.0.0.1')

    def test_invalid_camera_and_optional_ocr(self):
        with self.assertRaises(ValueError):
            camera_command('file:///video.mp4', Path('data/demo'), 12345, 'demo/light', 'simulation-test')
        args = camera_command('http://camera/capture', Path('data/demo'), 12345, 'demo/light', 'simulation-test', False, False)
        self.assertNotIn('--plate-ocr', args)
        self.assertNotIn('--select-line', args)


@unittest.skipUnless(Path('C:/Program Files/mosquitto/mosquitto.exe').is_file(), 'Mosquitto is not installed')
class SimulatedLightTests(unittest.TestCase):
    def test_real_mqtt_colors_timeout_and_owned_broker_cleanup(self):
        with tempfile.TemporaryDirectory() as output:
            light = SimulatedLight(output)
            process = light.process
            receiver = MqttLight('127.0.0.1', light.port, topic=light.topic, device=light.device, stale_after=.4)
            def wait_color(color):
                deadline = time.monotonic()+4
                while receiver.state.current() != color:
                    if time.monotonic() >= deadline: self.fail(f'Expected {color}, got {receiver.state.current()}')
                    time.sleep(.02)
            try:
                receiver.start()
                deadline = time.monotonic()+4
                while not receiver.client.is_connected():
                    if time.monotonic() >= deadline: self.fail('Receiver did not connect')
                    time.sleep(.02)
                time.sleep(.05)
                light.publish()
                wait_color('GREEN')
                light.set_state('RED')
                wait_color('RED')
                light.set_state('YELLOW')
                wait_color('YELLOW')
                light.set_state('UNKNOWN')
                wait_color('UNKNOWN')
                light.set_state('GREEN')
                wait_color('GREEN')
            finally:
                receiver.stop()
                light.close()
            self.assertIsNotNone(process.poll())


if __name__ == '__main__':
    unittest.main()
