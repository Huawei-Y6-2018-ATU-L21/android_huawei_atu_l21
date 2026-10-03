#!/usr/bin/env python3
"""Makes console-ramoops and pmsg-ramoops files pulled from pstore readable.
Usage: pull_pstore.py DIR   (DIR/pstore/* -> DIR/console.txt, DIR/logcat-pmsg.txt)"""
import os, struct, sys
d = sys.argv[1]
c = open(os.path.join(d, 'pstore/console-ramoops'), 'rb').read().replace(b'\0', b'')
open(os.path.join(d, 'console.txt'), 'wb').write(c)
out = []
p = os.path.join(d, 'pstore/pmsg-ramoops-0')
if os.path.exists(p):
    b = open(p, 'rb').read(); i = 0
    while True:
        i = b.find(b'l', i)
        if i < 0 or i + 19 > len(b): break
        try:
            ln, uid, pid = struct.unpack_from('<HHH', b, i + 1)
            lid, tid, sec, nsec = struct.unpack_from('<BHII', b, i + 7)
            body = b[i + 18:i + ln]
            if 4 < ln < 5000 and body and body[0] <= 8:
                parts = body[1:].split(b'\0'); tag = parts[0].decode(errors='replace')
                msg = (parts[1] if len(parts) > 1 else b'').decode(errors='replace')
                if tag.isprintable() and 0 < len(tag) < 40:
                    pr = 'VDIWEF'[body[0] - 2] if 2 <= body[0] <= 7 else str(body[0])
                    out.append(f"{sec:>10}.{nsec // 1000000:03d} {pid:5} {pr} {tag}: {msg}")
                    i += ln; continue
        except Exception:
            pass
        i += 1
open(os.path.join(d, 'logcat-pmsg.txt'), 'w').write('\n'.join(out))
print(f"console: {c.count(b'\n')} lines, logcat: {len(out)} records")
