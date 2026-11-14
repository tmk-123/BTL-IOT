"""Read-only local event export with durable acknowledgements and offline retry."""

import argparse
import base64
from contextlib import closing
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sqlite3
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
IMAGE_KEYS = ('raw_image', 'annotated_image', 'vehicle_image', 'plate_image')
LOG = logging.getLogger('cloud_sync')


def envelope(event, evidence_root):
    result, images = dict(event), {}
    root = Path(evidence_root).resolve()
    for key in IMAGE_KEYS:
        name = event.get(key)
        if name:
            path = Path(name).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Evidence outside configured directory: ' + key)
            content = path.read_bytes()
            if len(content) > 5 * 1024 * 1024:
                raise ValueError('Evidence exceeds 5 MiB: ' + key)
            images[key] = base64.b64encode(content).decode('ascii')
            result[key] = True
        else:
            result[key] = None
    result['source'] = 'edge-camera'
    return {'event': result, 'images': images}


def post_event(url, token, body):
    request = urllib.request.Request(url.rstrip('/') + '/events',
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}, method='POST')
    # urllib verifies the TLS certificate using the system trust store.
    with urllib.request.urlopen(request, timeout=30) as response:
        reply = json.load(response)
    if reply.get('event_id') != body['event']['event_id'] or type(reply.get('inserted')) is not bool:
        raise ValueError('Invalid acknowledgement from cloud')


def sync_once(config, sender=post_event):
    database = Path(config['database']).resolve()
    state_path = Path(config.get('state', ROOT / 'data/cloud_sync.db'))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    sent, failed = 0, 0
    with closing(sqlite3.connect(state_path, timeout=5)) as state:
        state.execute('CREATE TABLE IF NOT EXISTS sent (server TEXT, event_id TEXT, PRIMARY KEY(server,event_id))')
        state.commit()
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=5)) as local:
            # Fetch in pages so a large backlog does not hold the writer's read lock.
            cursor = ''
            while True:
                rows = local.execute('SELECT event_id,payload_json FROM events WHERE event_id>? ORDER BY event_id LIMIT 100',
                                     (cursor,)).fetchall()
                if not rows:
                    break
                for event_id, payload in rows:
                    cursor = event_id
                    if state.execute('SELECT 1 FROM sent WHERE server=? AND event_id=?',
                                     (config['url'], event_id)).fetchone():
                        continue
                    try:
                        body = envelope(json.loads(payload), config['evidence_dir'])
                        sender(config['url'], config['token'], body)
                        state.execute('INSERT OR IGNORE INTO sent VALUES (?,?)', (config['url'], event_id))
                        state.commit()
                        sent += 1
                    except Exception as error:
                        failed += 1
                        # Do not log URLs, keys, plate data or full server responses.
                        LOG.warning('Pending event %s (%s)', event_id, type(error).__name__)
                        if isinstance(error, urllib.error.URLError):
                            if not isinstance(error, urllib.error.HTTPError) or error.code in (401, 403, 429) or error.code >= 500:
                                # Retry next cycle instead of timing out once for every queued event.
                                return sent, failed
                if len(rows) < 100:
                    break
    return sent, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'data/cloud_sync.json')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--log-file', type=Path)
    args = parser.parse_args()
    handlers = None
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers = [RotatingFileHandler(args.log_file, maxBytes=2_000_000, backupCount=2, encoding='utf-8')]
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=handlers)
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    parsed = urlsplit(config['url'])
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Cloud URL must be HTTPS without credentials, query or fragment')
    if len(config['token']) < 32:
        raise ValueError('API token is too short')
    while True:
        try:
            sent, failed = sync_once(config)
            LOG.info('Synced=%s pending_errors=%s', sent, failed)
            if args.once:
                return 1 if failed else 0
        except (OSError, sqlite3.Error) as error:
            LOG.warning('Sync unavailable (%s); local data retained', type(error).__name__)
            if args.once:
                return 1
        time.sleep(max(5, config.get('interval_seconds', 15)))


if __name__ == '__main__':
    raise SystemExit(main())
