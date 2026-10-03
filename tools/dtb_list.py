#!/usr/bin/env python3
"""Lists the DTBs appended to an Image.gz-dtb / kernel.img (model, msm-id, board-id).

Usage:
  dtb_list.py FILE [--extract DIR]
FILE may be an Android boot image (kernel.img) or a raw Image.gz-dtb.
"""
import os
import struct
import subprocess
import sys


def payload(path):
    d = open(path, "rb").read()
    if d[:8] == b"ANDROID!":
        ks = struct.unpack_from("<I", d, 8)[0]
        ps = struct.unpack_from("<I", d, 36)[0]
        return d[ps:ps + ks]
    return d


def dtbs(blob):
    i = 0
    while True:
        i = blob.find(b"\xd0\x0d\xfe\xed", i)
        if i < 0:
            return
        size = struct.unpack_from(">I", blob, i + 4)[0]
        if 0x100 < size < 0x400000:
            yield i, blob[i:i + size]
            i += size
        else:
            i += 4


def props(dtb):
    src = subprocess.run(["dtc", "-I", "dtb", "-O", "dts", "-q", "-"], input=dtb,
                         capture_output=True).stdout.decode(errors="replace")
    out = {}
    for line in src.splitlines()[:80]:
        line = line.strip()
        for key in ("model", "qcom,msm-id", "qcom,board-id", "huawei,hw_type", "compatible"):
            if line.startswith(key + " ") or line.startswith(key + "="):
                out.setdefault(key, line.split("=", 1)[1].strip().rstrip(";"))
    return out


def main():
    path = sys.argv[1]
    ext = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--extract" else None
    if ext:
        os.makedirs(ext, exist_ok=True)
    for n, (off, dtb) in enumerate(dtbs(payload(path))):
        p = props(dtb)
        print(f"{n:3d} @{off:#010x} {len(dtb):7d}  {p.get('model','?')} | msm-id {p.get('qcom,msm-id','?')} | board-id {p.get('qcom,board-id','?')}")
        if ext:
            open(os.path.join(ext, f"{n:03d}.dtb"), "wb").write(dtb)


if __name__ == "__main__":
    main()
