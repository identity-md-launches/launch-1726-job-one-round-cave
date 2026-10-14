#!/usr/bin/env python3
"""Conserve the ancestor outside the image-tool addition; make required thumbnail."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path.cwd().resolve()
WALL = ROOT / 'artifacts/line-4/wall.png'
OUTPUT = ROOT / 'artifacts/line-4/wall-v18.png'
PATCH = (695, 235, 820, 325)


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def main():
    ancestor_hash = hashlib.sha256(WALL.read_bytes()).hexdigest()
    assert ancestor_hash == 'd2d2b075e872f28c1971ceb0d2443906d613309fb396bfa203d49f4ced6717b2'
    spec = importlib.util.spec_from_file_location('codec38', ROOT/'line-4/tools/call-rehearsal/thumbnail.py')
    codec = importlib.util.module_from_spec(spec); spec.loader.exec_module(codec)
    width, height, old = codec.png_rgb(WALL)
    sw, sh, generated = codec.png_rgb(OUTPUT)
    assert (width, height) == (sw, sh) == (1254, 1254)
    source_hash = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    left, top, right, bottom = PATCH
    rows = [bytearray(row) for row in old]
    for y in range(top, bottom):
        for x in range(left, right):
            red, green, blue = generated[y][3*x:3*x+3]
            previous = old[y][3*x:3*x+3]
            changed = max(abs(a-b) for a,b in zip((red,green,blue),previous)) > 15
            bowl = 704 <= x <= 812 and 266 <= y <= 319
            chalk = (x-757)**2+(y-253)**2 <= 11**2
            pigment = ((bowl and (red > 1.48*green and red-green > 38 or
                                  green < 88 and red < 125)) or
                       chalk)
            if pigment and (changed or chalk):
                rows[y][3*x:3*x+3] = generated[y][3*x:3*x+3]
    inside = outside = 0
    for y in range(height):
        for x in range(width):
            if rows[y][3*x:3*x+3] != old[y][3*x:3*x+3]:
                if left <= x < right and top <= y < bottom: inside += 1
                else: outside += 1
    assert inside > 0 and outside == 0
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',width,height,8,2,0,0,0))
           + chunk(b'IDAT',zlib.compress(b''.join(b'\0'+bytes(row) for row in rows),9)) + chunk(b'IEND',b''))
    jpeg = codec.jpeg(codec.resize(width,height,rows,512))
    assert len(jpeg) < 100000
    OUTPUT.write_bytes(png); WALL.write_bytes(png)
    with (ROOT/'dist/line-4/38.jpg').open('wb') as handle: handle.write(jpeg)
    checks = {'ancestor_sha256':ancestor_hash,'generated_sha256':source_hash,
              'wall_sha256':hashlib.sha256(png).hexdigest(),
              'wall':{'width':width,'height':height,'format':'PNG','mode':'RGB','bytes':len(png)},
              'thumbnail':{'width':512,'height':512,'format':'JPEG','bytes':len(jpeg)},
              'addition_rectangle':list(PATCH),'changed_pixels_inside':inside,'changed_pixels_outside':outside,
              'unmet_visual_requirements':['Inherited tiny three-pronged trail motifs cannot be certified as five-digit handprints; preserved unchanged.']}
    (ROOT/'line-4/delivery-checks-38.json').write_text(json.dumps(checks,indent=2)+'\n')
    record = {'name':'The Evidence Sieve','image':'https://api.imd.fun/artifacts/'+checks['wall_sha256'],
              'attributes':[{'trait_type':'Cave','value':'Moss'}, {'trait_type':'Wall','value':'Line 4'},
                            {'trait_type':'Number','value':38}, {'trait_type':'Left behind','value':'Rehearsal Report'},
                            {'trait_type':'Meaning','value':'An ochre sieve catches a chalk pebble, filtering malformed call evidence before review.'},
                            {'trait_type':'One thing','value':'Rehearse Ethereum contract calls before submission'}]}
    with (ROOT/'dist/line-4/38.json').open('w') as handle: handle.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__ == '__main__': main()
