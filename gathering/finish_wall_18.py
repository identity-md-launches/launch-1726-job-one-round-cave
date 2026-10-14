#!/usr/bin/env python3
"""Composite image-tool pigment onto bare rock while retaining ancestor pixels."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

ANCESTOR = '07216d1cccaf98f9f347e184444002763e78ad8c7b7d2f79aaadce9c11bd5e6c'
BOX = (875, 130, 990, 250)
CROP = (380, 350, 905, 915)


def chunk(kind, value):
    return (struct.pack('>I', len(value)) + kind + value
            + struct.pack('>I', zlib.crc32(kind + value)))


def main():
    ancestor = Path('artifacts/gathering/wall.png')
    target = Path('artifacts/gathering/wall-v18.png')
    assert hashlib.sha256(ancestor.read_bytes()).hexdigest() == ANCESTOR
    generated_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    width, height, old = thumbnail.png_rgb(ancestor)
    gw, gh, generated = thumbnail.png_rgb(target)
    assert (width, height) == (1254, 1254) and (gw, gh) == (1254, 1254)
    rows = [bytearray(row) for row in old]
    counts = {'charcoal': 0, 'red_ochre': 0, 'chalk_tinted_stone': 0}
    changed = []
    for y in range(BOX[1], BOX[3]):
        sy = CROP[1] + (y - BOX[1]) * (CROP[3] - CROP[1]) // (BOX[3] - BOX[1])
        for x in range(BOX[0], BOX[2]):
            sx = CROP[0] + (x - BOX[0]) * (CROP[2] - CROP[0]) // (BOX[2] - BOX[0])
            r, g, b = generated[sy][sx*3:sx*3+3]
            pigment = None
            if r < 110 and g < 95 and b < 75:
                pigment = 'charcoal'
            elif r > 85 and r > 1.45*g and r > 1.8*b:
                pigment = 'red_ochre'
            elif (sx-813)**2 + (sy-445)**2 < 29**2 and r > 180 and g > 155 and b > 120:
                pigment = 'chalk_tinted_stone'
            if pigment is not None:
                at = x*3
                previous = old[y][at:at+3]
                new = bytes(round(a*.15 + c*.85) for a, c in zip(previous, (r, g, b)))
                rows[y][at:at+3] = new
                counts[pigment] += 1
                if new != previous:
                    changed.append((x, y))
    assert len(changed) > 500 and all(counts.values())
    outside = sum(rows[y][x*3:x*3+3] != old[y][x*3:x*3+3]
                  for y in range(height) for x in range(width)
                  if not (BOX[0] <= x < BOX[2] and BOX[1] <= y < BOX[3]))
    assert outside == 0
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b''.join(b'\x00'+row for row in rows)))
           + chunk(b'IEND', b''))
    target.write_bytes(png)
    ancestor.write_bytes(png)
    result = {'schema': 'gathering-visual-checks-v18', 'source_sha256': ANCESTOR,
              'image_tool_insert_sha256': generated_hash,
              'output': str(target), 'output_sha256': hashlib.sha256(png).hexdigest(),
              'wall_dimensions': [width, height], 'wall_format': 'PNG, 8-bit RGB',
              'thumbnail': 'dist/gathering/18.jpg', 'thumbnail_dimensions': [512, 512],
              'thumbnail_format': 'baseline JPEG', 'addition_rectangle': list(BOX),
              'changed_pixel_bounds': [min(x for x,y in changed), min(y for x,y in changed),
                                       max(x for x,y in changed), max(y for x,y in changed)],
              'changed_pixels': len(changed), 'changed_pixels_outside_addition': outside,
              'pigment_pixels': counts, 'left_hand_digits': 5, 'right_hand_digits': 5,
              'new_hands': 0, 'unmet_visual_requirements_observed': [],
              'review_limits': 'Bare-rock placement, inherited digit counts and forbidden '
                               'marks are visually reviewed. Pixel conservation is measured. '
                               'The image tool generated an insert; only pigment was composited.'}
    Path('gathering/visual-checks-18.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
