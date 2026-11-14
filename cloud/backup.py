"""Daily on-server recovery copy; immutable evidence can be copied after pg_dump."""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time

os.umask(0o077)
root = Path('/var/backups/traffic-iot')
root.mkdir(mode=0o700, parents=True, exist_ok=True)
name = datetime.now(timezone.utc).strftime('traffic-%Y%m%dT%H%M%SZ.tar.gz')
pending = root / (name + '.pending')
try:
    with tempfile.TemporaryDirectory(prefix='traffic-backup-') as temporary:
        dump = Path(temporary) / 'traffic_iot.dump'
        with dump.open('wb') as output:
            subprocess.run(['runuser', '-u', 'traffic-iot', '--', 'pg_dump', '-Fc', 'traffic_iot'],
                           stdout=output, check=True)
        with tarfile.open(pending, 'w:gz') as archive:
            archive.add(dump, arcname='traffic_iot.dump')
            archive.add('/var/lib/traffic-iot/evidence', arcname='evidence')
        pending.replace(root / name)
    for old in root.glob('traffic-*.tar.gz'):
        if old.is_file() and old.stat().st_mtime < time.time() - 7 * 86400:
            old.unlink()
    print('Database and evidence backup complete')
finally:
    pending.unlink(missing_ok=True)
