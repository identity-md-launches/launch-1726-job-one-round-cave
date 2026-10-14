"""Keep the inherited cave exactly, adding only the editor's new rock motif."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'wall_thumbnail_38', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)

ancestor_path = ROOT / 'artifacts/line-3/wall.png'
output_path = ROOT / 'artifacts/line-3/wall-v18.png'
ancestor_png = ancestor_path.read_bytes()
ancestor_hash = hashlib.sha256(ancestor_png).hexdigest()
assert ancestor_hash == '38eb883043aecd11679daa4fe2eaa5d3ac8ed37f00297fa1cab72612e598272c'
w, h, ancestor = thumbnail.png_rgb(ancestor_path)
gw, gh, generated = thumbnail.png_rgb(output_path)
assert (w, h) == (gw, gh) == (1254, 1254)

# The generated wall supplies the pigment. Restrict it to unused rock, leaving
# every ancestor pixel outside the addition untouched. A short feather avoids
# a rectangular transition in the torchlit stone.
box = (975, 651, 1117, 777)
feather = 9
rows = [bytearray(row) for row in ancestor]
for y in range(box[1], box[3]):
    for x in range(box[0], box[2]):
        inset = min(x - box[0], box[2] - 1 - x,
                    y - box[1], box[3] - 1 - y)
        alpha = min(1.0, max(0.0, inset / feather))
        start = 3 * x
        for c in range(3):
            old = ancestor[y][start + c]
            new = generated[y][start + c]
            rows[y][start + c] = round(old * (1 - alpha) + new * alpha)

def chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload)))

png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(b''.join(b'\0' + row for row in rows), 9))
       + chunk(b'IEND', b''))
changed = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(h) for x in range(w))
outside = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(h) for x in range(w)
              if not (box[0] <= x < box[2] and box[1] <= y < box[3]))
assert changed > 0 and outside == 0
output_path.write_bytes(png)
ancestor_path.write_bytes(png)

jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
assert len(jpeg) < 100_000
(ROOT / 'dist/line-3/38.jpg').write_bytes(jpeg)
digest = hashlib.sha256(png).hexdigest()
report = {
    'ancestor_sha256': ancestor_hash, 'wall_sha256': digest,
    'format': 'PNG', 'dimensions': [w, h], 'mode': 'RGB 8-bit',
    'addition_box': list(box), 'changed_pixels': changed,
    'changed_pixels_outside_addition': outside,
    'thumbnail': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
    'unmet_visual_requirements': [], 'visual_review': 'pending',
}
(ROOT / 'line-3/visual-checks-38.json').write_text(json.dumps(report, indent=2) + '\n')
record = {
    'name': 'The Open Trail',
    'image': 'https://api.imd.fun/artifacts/' + digest,
    'attributes': [
        {'trait_type': 'Cave', 'value': 'Moss'},
        {'trait_type': 'Wall', 'value': 'Line 3'},
        {'trait_type': 'Number', 'value': 38},
        {'trait_type': 'Left behind', 'value': 'Code Dependency Frontier'},
        {'trait_type': 'Meaning', 'value': 'Pepe maps proved call targets and leaves unresolved branches visible.'},
        {'trait_type': 'One thing', 'value': 'Ethereum executable code identity'},
    ],
}
(ROOT / 'dist/line-3/38.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(report, indent=2))
