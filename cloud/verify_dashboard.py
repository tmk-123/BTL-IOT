"""Exercise the deployed Streamlit app against the real read-only API."""
import os
from pathlib import Path
import pwd
import sys

for line in Path('/etc/traffic-iot/dashboard.env').read_text().splitlines():
    key, value = line.split('=', 1)
    os.environ[key] = value
account = pwd.getpwnam('traffic-dashboard')
os.setgroups([])
os.setgid(account.pw_gid)
os.setuid(account.pw_uid)
os.environ['HOME'] = account.pw_dir
sys.path.insert(0, '/opt/traffic-iot/dashboard')

from dashboard_cloud import load_cloud_events, load_cloud_image
from PIL import Image
from io import BytesIO
from streamlit.testing.v1 import AppTest

rows, total, summary = load_cloud_events(limit=1)
assert total >= 1 and sum(summary.values()) == total
app = AppTest.from_file('/opt/traffic-iot/dashboard/dashboard.py', default_timeout=30).run()
assert not app.exception, 'Dashboard failed'
assert not app.error, 'API connection failed'
assert not any(box.key == 'dataset' for box in app.selectbox)
default_count = app.metric[0].value
app.selectbox(key='violation_color').select('YELLOW').run()
assert not app.exception and not app.error
app.selectbox(key='violation_color').select(None).run()
buttons = [button for button in app.button if button.key and button.key.startswith('details:')]
assert buttons, 'Expected synced events in dashboard'
buttons[0].click().run()
assert not app.exception, 'Detail dialog failed'
assert not any('Chưa tải được ảnh' in warning.value for warning in app.warning), 'Detail image failed'
app.text_input(key='search').input('NO-SUCH-PLATE-TEST').run()
assert app.metric[0].value == '0' and not app.exception
app.text_input(key='search').input('').run()
app.checkbox(key='show_journal').check().run()
assert not app.exception and not app.error
sample, _, _ = load_cloud_events(assessment=('suspected_red_light', 'suspected_yellow_light'), limit=1)
with Image.open(BytesIO(load_cloud_image(sample[0]['annotated_image']))) as image:
    image.verify()
print(f'PASS: real API, {total} events, suspected total={default_count}, color filter, detail photos, search, journal')
