"""Check HTTPS login protection and read-only API scope without printing credentials."""
import base64
import json
import http.client
import os
from pathlib import Path
import urllib.error
import urllib.request

access = json.loads(Path('/etc/traffic-iot/dashboard_access.json').read_text())
read_token = next(line.split('=', 1)[1] for line in Path('/etc/traffic-iot/dashboard.env').read_text().splitlines()
                  if line.startswith('IOT_READ_TOKEN='))
auth = 'Basic ' + base64.b64encode((access['username'] + ':' + access['password']).encode()).decode()


def request(url, authorization=None, data=None):
    headers = {'Content-Type': 'application/json'}
    if authorization:
        headers['Authorization'] = authorization
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers, data=data), timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


url = access['url']
assert request(url)[0] == 401
assert request(url, 'Basic aW52YWxpZDppbnZhbGlk')[0] == 401
assert request(url, auth)[0] == 200
assert request(url + '_stcore/health')[0] == 401
assert request(url + '_stcore/health', auth)[0] == 200
assert request(url + 'media/nonexistent.jpg')[0] == 401
api = 'https://jenkins.tienichnhanong.com/iot-api'
status, body = request(api + '/events?limit=1', 'Bearer ' + read_token)
assert status == 200
result = json.loads(body)
assert result['total'] >= 1 and sum(result['summary'].values()) == result['total']
assert request(api + '/events', 'Bearer ' + read_token, b'{}')[0] == 401
assert request(api + '/events?search=%25', 'Bearer ' + read_token)[0] == 200
assert json.loads(request(api + '/events?search=%25', 'Bearer ' + read_token)[1])['total'] == 0
page_two = json.loads(request(api + '/events?limit=1&offset=1', 'Bearer ' + read_token)[1])
assert page_two['total'] == result['total'] and page_two['summary'] == result['summary']
assert page_two['events'][0]['event_id'] != result['events'][0]['event_id']
filtered = json.loads(request(api + '/events?assessment=suspected_red_light&assessment=suspected_yellow_light&light_state=YELLOW',
                              'Bearer ' + read_token)[1])
assert all(row['assessment'] == 'suspected_yellow_light' and row['light_state'] == 'YELLOW'
           for row in filtered['events'])
assert request(api + '/events?date_from=2026-11-15&date_to=2026-11-01', 'Bearer ' + read_token)[0] == 422
connection = http.client.HTTPSConnection('jenkins.tienichnhanong.com', timeout=15)
connection.request('GET', '/traffic/_stcore/stream', headers={
    'Authorization': auth, 'Connection': 'Upgrade', 'Upgrade': 'websocket',
    'Sec-WebSocket-Key': base64.b64encode(os.urandom(16)).decode(),
    'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Protocol': 'streamlit',
    'Origin': 'https://jenkins.tienichnhanong.com'})
response = connection.getresponse()
assert response.status == 101, 'WebSocket upgrade failed: ' + str(response.status)
connection.close()
print('PASS: HTTPS login, wrong password rejected, protected health/media/WebSocket, read-only API, literal search, pagination, filters')
