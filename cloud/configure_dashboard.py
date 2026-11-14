"""Provision read-only dashboard credentials and add a protected Caddy route."""
import json
from pathlib import Path
import secrets
import re
import shutil
import subprocess
import time

directory = Path('/etc/traffic-iot')
api_env = directory / 'api.env'
lines = api_env.read_text().splitlines()
read_token = next((line.split('=', 1)[1] for line in lines if line.startswith('IOT_READ_TOKEN=')), None)
if read_token is None:
    read_token = secrets.token_urlsafe(48)
    shutil.copy2(api_env, directory / ('api.env.before-dashboard-' + str(int(time.time()))))
    api_env.write_text('\n'.join(lines) + '\nIOT_READ_TOKEN=' + read_token + '\n')
    api_env.chmod(0o600)
env = directory / 'dashboard.env'
env.write_text('IOT_CLOUD_URL=http://127.0.0.1:8765\nIOT_READ_TOKEN=' + read_token + '\n')
env.chmod(0o600)

access_path = directory / 'dashboard_access.json'
if not access_path.exists():
    access_path.write_text(json.dumps({'url': 'https://jenkins.tienichnhanong.com/traffic/',
                                     'username': 'giamsat', 'password': secrets.token_urlsafe(18)}, indent=2))
    access_path.chmod(0o600)
access = json.loads(access_path.read_text())
caddy = Path('/etc/caddy/Caddyfile')
original = caddy.read_text()
if 'handle /traffic/*' not in original:
    marker = '    handle {\n'
    if original.count(marker) != 1:
        raise RuntimeError('Unexpected Caddy configuration; refusing to replace')
    hashed = subprocess.run(['caddy', 'hash-password'], input=access['password'] + '\n',
                            text=True, capture_output=True, check=True).stdout.strip()
    version = subprocess.run(['caddy', 'version'], text=True, capture_output=True, check=True).stdout
    match = re.search(r'v?(\d+)\.(\d+)', version)
    if not match:
        raise RuntimeError('Cannot identify Caddy version')
    auth_directive = 'basic_auth' if tuple(map(int, match.groups())) >= (2, 8) else 'basicauth'
    block = '''    redir /traffic /traffic/ 308
    handle /traffic/* {
        basic_auth {
            USERNAME PASSWORD_HASH
        }
        header Cache-Control "private, no-store"
        reverse_proxy 127.0.0.1:8501
    }
'''.replace('USERNAME', access['username']).replace('PASSWORD_HASH', hashed).replace('basic_auth', auth_directive)
    candidate = caddy.with_name('Caddyfile.dashboard-candidate')
    candidate.write_text(original.replace(marker, block + marker))
    subprocess.run(['caddy', 'validate', '--config', str(candidate), '--adapter', 'caddyfile'], check=True)
    backup = caddy.with_name('Caddyfile.before-dashboard-' + str(int(time.time())))
    shutil.copy2(caddy, backup)
    shutil.copyfile(candidate, caddy)
    try:
        subprocess.run(['systemctl', 'reload', 'caddy'], check=True)
    except BaseException:
        shutil.copyfile(backup, caddy)
        subprocess.run(['systemctl', 'reload', 'caddy'], check=False)
        raise
    candidate.unlink()
print('Dashboard credentials configured; Caddy route protected')
