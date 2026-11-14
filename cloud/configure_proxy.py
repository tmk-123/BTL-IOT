"""Add the IoT API route while retaining the existing Jenkins catch-all."""
from pathlib import Path
import shutil
import subprocess
import time

path = Path('/etc/caddy/Caddyfile')
original = path.read_text()
if 'handle_path /iot-api/*' not in original:
    old = '\treverse_proxy 127.0.0.1:8080'
    if original.count(old) != 1:
        raise RuntimeError('Unexpected Caddy configuration; no changes applied')
    replacement = '''\thandle_path /iot-api/* {
        request_body {
            max_size 32MB
        }
        reverse_proxy 127.0.0.1:8765
    }
    handle {
        reverse_proxy 127.0.0.1:8080
    }'''
    candidate = path.with_name('Caddyfile.iot-candidate')
    candidate.write_text(original.replace(old, replacement))
    subprocess.run(['caddy', 'validate', '--config', str(candidate), '--adapter', 'caddyfile'], check=True)
    backup = path.with_name('Caddyfile.before-iot-' + str(int(time.time())))
    shutil.copy2(path, backup)
    shutil.copyfile(candidate, path)
    try:
        subprocess.run(['systemctl', 'reload', 'caddy'], check=True)
    except BaseException:
        shutil.copyfile(backup, path)
        subprocess.run(['systemctl', 'reload', 'caddy'], check=False)
        raise
    candidate.unlink()
    print('Caddy route installed; previous configuration backed up')
else:
    print('IoT route already configured')
