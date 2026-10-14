#!/usr/bin/env python3
"""Consume an in-memory generated PNG and preserve the inherited wall pixels.

Run --terminal-base64 only for the image tool's in-memory delivery through a PTY.
Otherwise accepts PNG bytes on stdin. No standalone insert is saved.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import termios

import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = 'e9ca37a6bcf6743e3368f4c33fa38aacaa9fb124662bd832d2c3d12882148724'
PLACEMENT = (270, 1010, 180, 72)


def main():
    source = (ROOT / 'artifacts/line-2/wall.png').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('refusing a wall other than the verified record 37')
    width, height, channels, old = imageops.decode(source)
    if (width, height, channels) != (1254, 1254, 3):
        raise ValueError('unexpected inherited PNG format')
    if sys.argv[1:] == ['--terminal-base64']:
        original = termios.tcgetattr(0)
        raw = termios.tcgetattr(0)
        raw[3] &= ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(0, termios.TCSANOW, raw)
        print('ready for in-memory insert', flush=True)
        try:
            encoded = sys.stdin.buffer.readline(4_000_001)
            if len(encoded) > 4_000_000 or not encoded.endswith(b'\n'):
                raise ValueError('insert transport too large or unterminated')
            insert = base64.b64decode(encoded.strip(), validate=True)
        finally:
            termios.tcsetattr(0, termios.TCSANOW, original)
    elif not sys.argv[1:]:
        insert = sys.stdin.buffer.read(3_000_001)
        if len(insert) > 3_000_000:
            raise ValueError('insert too large')
    else:
        raise ValueError('unknown arguments')
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = PLACEMENT
    result, _ = imageops.composite(old, imageops.decode(insert))
    x, y, w, h = PLACEMENT
    for sy, (a, b) in enumerate(zip(old, result)):
        if not y <= sy < y+h:
            assert a == b
        else:
            assert a[:3*x] == b[:3*x] and a[3*(x+w):] == b[3*(x+w):]
    png = imageops.encode(width, height, result)
    for filename in ('wall.png', 'wall-v18.png'):
        (ROOT / 'artifacts/line-2' / filename).write_bytes(png)
    spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, result, 512))
    assert len(jpeg) < 100_000
    (ROOT / 'dist/line-2/38.jpg').write_bytes(jpeg)
    digest = hashlib.sha256(png).hexdigest()
    record = {'name': 'The Bound Pair', 'image': 'https://api.imd.fun/artifacts/' + digest,
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Moss'},
                  {'trait_type': 'Wall', 'value': 'Line 2'},
                  {'trait_type': 'Number', 'value': 38},
                  {'trait_type': 'Left behind', 'value': 'Allowance Code Context'},
                  {'trait_type': 'Meaning', 'value': 'Two looped stones bind spending permission to code at the same remembered moment.'},
                  {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'}]}
    (ROOT / 'dist/line-2/38.json').write_text(json.dumps(record, indent=2) + '\n')
    changed = sum(a[i:i+3] != b[i:i+3] for a, b in zip(old, result)
                  for i in range(0, len(a), 3))
    checks = {'source_sha256': SOURCE_SHA256, 'output_sha256': digest,
              'dimensions': [width, height], 'format': 'PNG', 'channels': '8-bit RGB',
              'placement': list(PLACEMENT), 'changed_pixels': changed,
              'outside_placement_unchanged': True,
              'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
              'unmet_visual_requirements': [],
              'visual_review': 'Pending inspection of final wall and JPEG.'}
    (ROOT / 'line-2/visual-checks-38.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks), flush=True)


if __name__ == '__main__':
    main()
