#!/bin/sh
# Run as root on the existing Ubuntu VPS, after copying cloud/ to /opt/traffic-iot.
set -eu
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=l
apt-get update -qq
apt-get install -y -qq postgresql python3-venv
id traffic-iot >/dev/null 2>&1 || useradd --system --home-dir /var/lib/traffic-iot --shell /usr/sbin/nologin traffic-iot
install -d -m 700 -o traffic-iot -g traffic-iot /var/lib/traffic-iot /var/lib/traffic-iot/evidence
install -d -m 700 /etc/traffic-iot
systemctl enable --now postgresql
if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='traffic-iot'" | grep -q 1; then
    runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c 'CREATE ROLE "traffic-iot" LOGIN'
fi
if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='traffic_iot'" | grep -q 1; then
    runuser -u postgres -- createdb --owner=traffic-iot traffic_iot
fi
python3 -m venv /opt/traffic-iot/venv
/opt/traffic-iot/venv/bin/pip install --quiet -r /opt/traffic-iot/requirements.txt
python3 - <<'PY'
from pathlib import Path
import json
import secrets
env = Path('/etc/traffic-iot/api.env')
if not env.exists():
    token = secrets.token_urlsafe(48)
    env.write_text('DATABASE_URL="dbname=traffic_iot user=traffic-iot host=/var/run/postgresql"\n'
                   'EVIDENCE_DIR=/var/lib/traffic-iot/evidence\nIOT_API_TOKEN=' + token + '\n')
    env.chmod(0o600)
    client = Path('/etc/traffic-iot/client.json')
    client.write_text(json.dumps({'url': 'https://jenkins.tienichnhanong.com/iot-api', 'token': token}))
    client.chmod(0o600)
PY
install -m 644 /opt/traffic-iot/traffic-iot.service /etc/systemd/system/traffic-iot.service
systemctl daemon-reload
systemctl enable --now traffic-iot
