#!/usr/bin/env python3
"""Replaces the whole cpio inside a Huawei ramdisk.img (boot image v0, ramdisk only).

The header (addresses, page size, cmdline) comes from the template image; the cmdline can be extended.
The new cpio is gzip-compressed (the stock kernel only supports CONFIG_RD_GZIP).

Usage:
  ramdisk_replace.py TEMPLATE.img NEW.cpio OUT.img [--append-cmdline "a=b c=d"]
"""
import argparse
import gzip
import hashlib
import struct

ap = argparse.ArgumentParser()
ap.add_argument("template")
ap.add_argument("cpio")
ap.add_argument("out")
ap.add_argument("--append-cmdline", default="")
a = ap.parse_args()

img = open(a.template, "rb").read()
assert img[:8] == b"ANDROID!"
ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack_from("<8I", img, 8)
assert ks == 0 and ss == 0
raw = open(a.cpio, "rb").read()
assert raw[:6] == b"070701", "expected a newc cpio"
rd = gzip.compress(raw, 9, mtime=0)

hdr = bytearray(img[:ps])
struct.pack_into("<I", hdr, 16, len(rd))
if a.append_cmdline:
    cmd = bytes(hdr[64:64 + 512]).split(b"\0")[0]
    cmd = (cmd + b" " + a.append_cmdline.encode()).strip()
    assert len(cmd) < 512, "cmdline exceeds 512 bytes"
    hdr[64:64 + 512] = cmd.ljust(512, b"\0")
sha = hashlib.sha1()
for blob in (b"", rd, b""):
    sha.update(blob)
    sha.update(struct.pack("<I", len(blob)))
hdr[576:608] = sha.digest().ljust(32, b"\0")
open(a.out, "wb").write(bytes(hdr) + rd + b"\0" * ((-len(rd)) % ps))
print(f"{a.out}: ramdisk {len(rd)} bytes, cmdline: {bytes(hdr[64:576]).split(b'\0')[0].decode()}")
