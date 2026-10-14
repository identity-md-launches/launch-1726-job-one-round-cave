#!/usr/bin/env python3
"""Keep the generated trail pigment, removing incidental insert-rock speckles."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zlib
import struct
from finish_wall_18 import ANCESTOR, BOX, CROP, chunk, thumbnail


def near_segment(x, y, a, b, radius):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return (x-a[0]-t*dx)**2 + (y-a[1]-t*dy)**2 <= radius**2


def main():
    path = Path('artifacts/gathering/wall-v18.png')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '2b59556382184e2363da169606c19633f4f25dc4c8b545382dc5f0ec5fa1d3fe'
    request = urllib.request.Request('https://api.imd.fun/artifacts/'+ANCESTOR,
                                    headers={'User-Agent': 'MossGathering18/1.0 (wall preservation)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(12000000)
    assert hashlib.sha256(data).hexdigest() == ANCESTOR
    ancestor = Path('artifacts/gathering/wall.png')
    ancestor.write_bytes(data)
    w,h,old = thumbnail.png_rgb(ancestor)
    _,_,painted = thumbnail.png_rgb(path)
    rows = [bytearray(row) for row in old]
    trail = [(530,880),(599,792),(638,696),(636,641)]
    left = [(638,641),(600,591),(530,550),(501,508),(482,465)]
    right = [(638,641),(691,575),(756,525),(777,489)]
    open_path = [(642,753),(700,723),(750,690),(792,685)]
    changed = []
    for y in range(BOX[1],BOX[3]):
        sy=CROP[1]+(y-BOX[1])*(CROP[3]-CROP[1])//(BOX[3]-BOX[1])
        for x in range(BOX[0],BOX[2]):
            sx=CROP[0]+(x-BOX[0])*(CROP[2]-CROP[0])//(BOX[2]-BOX[0])
            keep = ((sx-450)**2+(sy-414)**2 <= 58**2 or
                    (sx-813)**2+(sy-445)**2 <= 58**2 or
                    any(near_segment(sx,sy,a,b,23) for points in (trail,left,right,open_path)
                        for a,b in zip(points,points[1:])))
            at=x*3
            if keep and painted[y][at:at+3] != old[y][at:at+3]:
                rows[y][at:at+3]=painted[y][at:at+3]
                changed.append((x,y))
    assert len(changed)>500
    outside=sum(rows[y][3*x:3*x+3] != old[y][3*x:3*x+3]
                for y in range(h) for x in range(w)
                if not (BOX[0]<=x<BOX[2] and BOX[1]<=y<BOX[3]))
    assert outside==0
    png=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))
         +chunk(b'IDAT',zlib.compress(b''.join(b'\x00'+row for row in rows)))+chunk(b'IEND',b''))
    path.write_bytes(png);ancestor.write_bytes(png)
    p=Path('gathering/visual-checks-18.json');r=json.loads(p.read_text())
    r['initial_composite_sha256']=r['output_sha256']
    r['output_sha256']=hashlib.sha256(png).hexdigest()
    r['changed_pixels']=len(changed)
    r['changed_pixel_bounds']=[min(x for x,y in changed),min(y for x,y in changed),
                               max(x for x,y in changed),max(y for x,y in changed)]
    r['changed_pixels_outside_addition']=outside
    r['pigment_pixels_stage']='Initial extraction counts; final motif mask removed incidental insert-rock speckles.'
    p.write_text(json.dumps(r,indent=2)+'\n')
    # This round's thumbnail only; retain every earlier thumbnail.
    Path('dist/gathering/18.jpg').unlink()
    print(json.dumps(r))


if __name__=='__main__':
    main()
