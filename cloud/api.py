"""Authenticated, immutable event/evidence storage. Bind to loopback behind Caddy."""

import base64
import binascii
from datetime import date
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
import psycopg
from psycopg.types.json import Jsonb

IMAGE_KEYS = ('raw_image', 'annotated_image', 'vehicle_image', 'plate_image')
ROOT = Path(os.environ.get('EVIDENCE_DIR', '/var/lib/traffic-iot/evidence'))
MAX_IMAGE = 5 * 1024 * 1024


def connection():
    return psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)


@asynccontextmanager
async def lifespan(app):
    if len(os.environ.get('IOT_API_TOKEN', '')) < 32:
        raise RuntimeError('IOT_API_TOKEN must contain at least 32 characters')
    ROOT.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, payload JSONB NOT NULL,
            content_digest TEXT NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
        db.execute("CREATE INDEX IF NOT EXISTS events_observed ON events ((payload->>'observed_at'))")
        db.execute("CREATE INDEX IF NOT EXISTS events_plate ON events ((payload->>'plate_text'))")
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def authorize(request: Request):
    expected = 'Bearer ' + os.environ['IOT_API_TOKEN']
    if not hmac.compare_digest(request.headers.get('authorization', '').encode(), expected.encode()):
        raise HTTPException(401, 'Authentication required')


def authorize_read(request: Request):
    supplied = request.headers.get('authorization', '').encode()
    tokens = [os.environ['IOT_API_TOKEN'], os.environ.get('IOT_READ_TOKEN', '')]
    if not any(hmac.compare_digest(supplied, ('Bearer ' + token).encode()) for token in tokens if token):
        raise HTTPException(401, 'Authentication required')


@app.get('/health')
def health():
    with connection() as db:
        db.execute('SELECT 1')
    return {'status': 'ok'}


def prepare(envelope):
    """Validate before touching disk. Cloud metadata never contains local file paths."""
    if not isinstance(envelope, dict):
        raise HTTPException(422, 'Expected an object')
    event, images = envelope.get('event'), envelope.get('images', {})
    if not isinstance(event, dict) or not isinstance(images, dict):
        raise HTTPException(422, 'Invalid event/images')
    event = dict(event)
    for key in ('event_id', 'session_id', 'observed_at', 'assessment', 'light_state'):
        if not isinstance(event.get(key), str) or not 0 < len(event[key]) <= 512:
            raise HTTPException(422, 'Invalid ' + key)
    if set(images) - set(IMAGE_KEYS):
        raise HTTPException(422, 'Unknown image type')
    decoded = {}
    folder = hashlib.sha256(event['event_id'].encode()).hexdigest()
    for key in IMAGE_KEYS:
        value = images.get(key)
        if bool(event.get(key)) != (value is not None):
            raise HTTPException(422, 'Missing or unexpected evidence: ' + key)
        event[key] = None
        if value is not None:
            try:
                if not isinstance(value, str) or len(value) > (MAX_IMAGE * 4 // 3 + 8):
                    raise ValueError()
                content = base64.b64decode(value, validate=True)
                if not 0 < len(content) <= MAX_IMAGE or not content.startswith(b'\xff\xd8\xff'):
                    raise ValueError()
            except (ValueError, binascii.Error):
                raise HTTPException(422, 'Invalid JPEG: ' + key)
            digest = hashlib.sha256(content).hexdigest()
            event[key] = f'{folder}/{key}-{digest}.jpg'
            decoded[key] = content
    # Avoid persisting camera URLs, passwords or machine-specific source paths.
    event['source'] = 'edge-camera'
    try:
        canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError):
        raise HTTPException(422, 'Invalid JSON metadata')
    return event, decoded, hashlib.sha256(canonical.encode()).hexdigest()


@app.post('/events', dependencies=[Depends(authorize)])
def upload(envelope: dict):
    event, images, digest = prepare(envelope)
    with connection() as db:
        # Serialise concurrent retries for the same ID; do not overwrite old events.
        db.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (event['event_id'],))
        old = db.execute('SELECT content_digest FROM events WHERE event_id=%s', (event['event_id'],)).fetchone()
        if old:
            if old[0] != digest:
                raise HTTPException(409, 'Event ID already exists with different content')
            return {'event_id': event['event_id'], 'inserted': False}
        for key, content in images.items():
            target = ROOT / event[key]
            target.parent.mkdir(parents=True, exist_ok=True)
            # Content-addressed files remain safe across crashes and retries.
            fd, temporary = tempfile.mkstemp(prefix='.upload-', dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
        db.execute('INSERT INTO events (event_id,payload,content_digest) VALUES (%s,%s,%s)',
                   (event['event_id'], Jsonb(event), digest))
    return {'event_id': event['event_id'], 'inserted': True}


@app.get('/events', dependencies=[Depends(authorize_read)])
def events(limit: int = 25, offset: int = 0, assessment: list[str] | None = Query(default=None),
           light_state: str | None = None, date_from: date | None = None,
           date_to: date | None = None, search: str = ''):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, 'Invalid pagination')
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, 'Invalid date range')
    clauses, values = [], []
    if assessment:
        clauses.append("payload->>'assessment'=ANY(%s)")
        values.append(assessment)
    if light_state:
        clauses.append("payload->>'light_state'=%s")
        values.append(light_state)
    for operator, value in (('>=', date_from), ('<=', date_to)):
        if value:
            clauses.append(f"left(payload->>'observed_at',10){operator}%s")
            values.append(str(value))
    if len(search) > 128:
        raise HTTPException(422, 'Search too long')
    if search:
        clauses.append("strpos(lower(coalesce(payload->>'plate_text','')),lower(%s))>0")
        values.append(search)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with connection() as db:
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        total = db.execute('SELECT count(*) FROM events' + where, values).fetchone()[0]
        summary = dict(db.execute("SELECT payload->>'assessment',count(*) FROM events" + where +
                                  " GROUP BY payload->>'assessment'", values).fetchall())
        rows = db.execute('SELECT payload FROM events' + where +
                          " ORDER BY payload->>'observed_at' DESC, event_id DESC LIMIT %s OFFSET %s",
                          values + [limit, offset]).fetchall()
    return {'total': total, 'summary': summary, 'events': [row[0] for row in rows]}


@app.get('/evidence/{event_hash}/{filename}', dependencies=[Depends(authorize_read)])
def evidence(event_hash: str, filename: str):
    import re
    if not re.fullmatch(r'[a-f0-9]{64}', event_hash) or not re.fullmatch(
            r'(raw_image|annotated_image|vehicle_image|plate_image)-[a-f0-9]{64}\.jpg', filename):
        raise HTTPException(404)
    relative = f'{event_hash}/{filename}'
    with connection() as db:
        row = db.execute('SELECT 1 FROM events WHERE payload->>\'raw_image\'=%s OR payload->>\'annotated_image\'=%s '
                         'OR payload->>\'vehicle_image\'=%s OR payload->>\'plate_image\'=%s LIMIT 1',
                         (relative,) * 4).fetchone()
    target = ROOT / relative
    if not row or not target.is_file():
        raise HTTPException(404)
    return FileResponse(target, media_type='image/jpeg', headers={'Cache-Control': 'private, no-store'})
