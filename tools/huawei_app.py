#!/usr/bin/env python3
"""Huawei UPDATE.APP lister / extractor.

Usage:
  huawei_app.py list UPDATE.APP
  huawei_app.py extract UPDATE.APP OUTDIR [NAME ...]   (all images if no name is given)
"""
import os
import struct
import sys

MAGIC = 0xA55AAA55
# magic, header_len, unk1, hw_id, seq, size, date, time, type, blank, hcrc, block, blank2
HDR = struct.Struct("<III8sII16s16s16s16sHHH")


def entries(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        end = f.tell()
        f.seek(0)
        # There is padding before the first magic (usually 92 zero bytes)
        pos = f.read(4096).find(struct.pack("<I", MAGIC))
        if pos < 0:
            raise SystemExit("magic not found")
        while pos + HDR.size <= end:
            f.seek(pos)
            raw = f.read(HDR.size)
            magic, hlen, _, hw, seq, size, date, time, typ, _, _, block, _ = HDR.unpack(raw)
            if magic != MAGIC:
                break
            name = typ.split(b"\0")[0].decode("ascii", "replace")
            data_off = pos + hlen
            yield {
                "name": name, "size": size, "offset": data_off, "seq": seq,
                "hw": hw.split(b"\0")[0].decode("ascii", "replace"),
                "date": date.split(b"\0")[0].decode(), "time": time.split(b"\0")[0].decode(),
            }
            pos = data_off + size
            pos += (-pos) % 4


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "list":
        for e in entries(path):
            print(f"{e['name']:<24} {e['size']/1048576:10.2f} MB  seq=0x{e['seq']:08x}  {e['date']} {e['time']}")
    elif cmd == "extract":
        out = sys.argv[3]
        want = set(sys.argv[4:])
        os.makedirs(out, exist_ok=True)
        with open(path, "rb") as f:
            for e in entries(path):
                if want and e["name"] not in want:
                    continue
                dst = os.path.join(out, e["name"].lower() + ".img")
                f.seek(e["offset"])
                left = e["size"]
                with open(dst, "wb") as o:
                    while left:
                        chunk = f.read(min(left, 16 << 20))
                        o.write(chunk)
                        left -= len(chunk)
                print(f"{e['name']} -> {dst} ({e['size']} bytes)")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
