#!/bin/sh
set -eu
id traffic-dashboard >/dev/null 2>&1 || useradd --system --home-dir /var/lib/traffic-dashboard --shell /usr/sbin/nologin traffic-dashboard
install -d -m 700 -o traffic-dashboard -g traffic-dashboard /var/lib/traffic-dashboard
python3 -m venv /opt/traffic-iot/dashboard-venv
/opt/traffic-iot/dashboard-venv/bin/pip install --quiet -r /opt/traffic-iot/dashboard-requirements.txt
python3 /opt/traffic-iot/configure_dashboard.py
install -m 644 /opt/traffic-iot/traffic-dashboard.service /etc/systemd/system/traffic-dashboard.service
systemctl daemon-reload
systemctl restart traffic-iot
systemctl enable --now traffic-dashboard
