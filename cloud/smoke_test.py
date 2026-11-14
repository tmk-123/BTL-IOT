"""Exercise the deployed API through HTTPS; remove only this run's test event."""
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import urllib.error
import urllib.request
import uuid

import psycopg

config = json.loads(Path('/etc/traffic-iot/client.json').read_text())
account = pwd.getpwnam('traffic-iot')
os.setgroups([])
os.setgid(account.pw_gid)
os.setuid(account.pw_uid)
event_id = 'cloud-smoke:' + str(uuid.uuid4())
# Tiny valid JPEG; production photos are verified separately after initial sync.
image = base64.b64encode(b'\xff\xd8\xff\xd9').decode()
body = {'event': {'event_id': event_id, 'session_id': 'cloud-smoke',
        'observed_at': '2026-11-14T00:00:00+07:00', 'assessment': 'unverified',
        'light_state': 'UNKNOWN', 'raw_image': True, 'source': 'test'}, 'images': {'raw_image': image}}


def request(path, data=None, authenticated=True):
    headers = {'Content-Type': 'application/json'}
    if authenticated:
        headers['Authorization'] = 'Bearer ' + config['token']
    req = urllib.request.Request(config['url'] + path,
        data=None if data is None else json.dumps(data).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


try:
    assert request('/health')[0] == 200
    assert request('/events', authenticated=False)[0] == 401
    assert request('/events', body, False)[0] == 401
    status, reply = request('/events', body)
    assert status == 200 and json.loads(reply)['inserted'] is True, (status, reply)
    assert json.loads(request('/events', body)[1])['inserted'] is False
    body['event']['assessment'] = 'different'
    assert request('/events', body)[0] == 409
    body['event']['assessment'] = 'unverified'
    with psycopg.connect('dbname=traffic_iot user=traffic-iot') as db:
        payload = db.execute('SELECT payload FROM events WHERE event_id=%s', (event_id,)).fetchone()[0]
    route = '/evidence/' + payload['raw_image']
    assert request(route, authenticated=False)[0] == 401
    assert request(route)[1] == base64.b64decode(image)
    body['images']['raw_image'] = 'invalid'
    assert request('/events', body)[0] == 422
    print('PASS: HTTPS, auth, insert, duplicate retry, conflict, private evidence, invalid image')
finally:
    with psycopg.connect('dbname=traffic_iot user=traffic-iot') as db:
        db.execute('DELETE FROM events WHERE event_id=%s', (event_id,))
    folder = Path('/var/lib/traffic-iot/evidence') / hashlib.sha256(event_id.encode()).hexdigest()
    if folder.is_dir():
        shutil.rmtree(folder)
