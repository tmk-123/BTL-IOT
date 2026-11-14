"""Verify all stored evidence hashes without printing plate metadata or secrets."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import urllib.request

config = json.loads(Path('/etc/traffic-iot/client.json').read_text())
account = pwd.getpwnam('traffic-iot')
os.setgroups([])
os.setgid(account.pw_gid)
os.setuid(account.pw_uid)

import psycopg

root = Path('/var/lib/traffic-iot/evidence')
images = 0
sample = None
with psycopg.connect('dbname=traffic_iot user=traffic-iot') as db:
    rows = db.execute('SELECT payload FROM events').fetchall()
for (event,) in rows:
    for key in ('raw_image', 'annotated_image', 'vehicle_image', 'plate_image'):
        relative = event.get(key)
        if not relative:
            continue
        path = root / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert path.name == f'{key}-{digest}.jpg', 'Evidence hash mismatch'
        images += 1
        sample = relative
if sample:
    request = urllib.request.Request(config['url'] + '/evidence/' + sample,
                                    headers={'Authorization': 'Bearer ' + config['token']})
    with urllib.request.urlopen(request, timeout=20) as response:
        assert response.read() == (root / sample).read_bytes(), 'HTTPS image mismatch'
with urllib.request.urlopen('https://jenkins.tienichnhanong.com/login', timeout=20) as response:
    assert response.status == 200
print(f'Verified {len(rows)} events, {images} evidence files; private HTTPS image and Jenkins OK')
