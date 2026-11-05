"""Save a detected plate once, then keep a confirmed snapshot in the same event folder."""

import json
from pathlib import Path
import time


class PlateAutoSaver:
    def __init__(self, output, source, save):
        self.output = Path(output)
        self.source = source
        self.save = save
        self.entries = {}

    def update(self, frame, preview, results, tracks):
        if len(results) != len(tracks):
            raise ValueError('Auto-save requires one track per plate detection')
        now = time.monotonic()
        self.entries = {key: value for key, value in self.entries.items() if now-value['last_seen'] < 60}
        saved_paths = []
        for result, track in zip(results, tracks):
            changed = False
            identity = track['track_id']
            entry = self.entries.get(identity)
            if entry is None:
                folder = self.save(frame, preview, [result], self.output, self.source, [track])
                entry = {'folder': folder, 'confirmed': False, 'stable_text': None, 'last_seen': now}
                self.entries[identity] = entry
                saved_paths.append(folder)
                changed = True
            entry['last_seen'] = now
            stable = track.get('stable_text')
            if stable and not entry['confirmed']:
                folder = self.save(frame, preview, [result], self.output, self.source, [track],
                                   target=entry['folder'] / 'confirmed')
                entry['confirmed'] = True
                entry['stable_text'] = stable
                saved_paths.append(folder)
                changed = True
            if changed:
                metadata = {'source': self.source, 'track_id': identity,
                            'status': 'consensus' if entry['confirmed'] else 'detected',
                            'stable_text': entry['stable_text'],
                            'detected_result': 'result.json',
                            'confirmed_result': 'confirmed/result.json' if entry['confirmed'] else None}
                # A small replace keeps readers from seeing half-written event metadata.
                temporary = entry['folder'] / 'event.tmp'
                temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
                temporary.replace(entry['folder'] / 'event.json')
        return saved_paths
