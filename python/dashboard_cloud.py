"""Server-side read-only API client; credentials never enter browser URLs."""
import json
import os
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def get(path, query=None):
    url = os.environ['IOT_CLOUD_URL'].rstrip('/')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname == '127.0.0.1'):
        raise ValueError('Cloud API requires HTTPS or server loopback')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Invalid cloud API configuration')
    if query:
        path += '?' + urlencode(query, doseq=True)
    request = Request(url + path, headers={'Authorization': 'Bearer ' + os.environ['IOT_READ_TOKEN']})
    with urlopen(request, timeout=15) as response:
        return response.read()


def load_cloud_events(database=None, assessment=None, light_state=None, date_from=None,
                      date_to=None, search='', limit=25, offset=0, **unused):
    query = {'limit': limit, 'offset': offset, 'search': search}
    if assessment:
        query['assessment'] = [assessment] if isinstance(assessment, str) else list(assessment)
    for key, value in (('light_state', light_state), ('date_from', date_from), ('date_to', date_to)):
        if value is not None:
            query[key] = str(value)
    data = json.loads(get('/events', query))
    rows = [dict(row, payload_json=json.dumps(row, ensure_ascii=False)) for row in data['events']]
    return rows, data['total'], data['summary']


def load_cloud_image(relative):
    if not re.fullmatch(r'[a-f0-9]{64}/(?:raw_image|annotated_image|vehicle_image|plate_image)-[a-f0-9]{64}\.jpg', relative):
        raise ValueError('Invalid evidence reference')
    return get('/evidence/' + relative)
