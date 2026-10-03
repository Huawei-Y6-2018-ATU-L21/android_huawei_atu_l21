#!/usr/bin/env python3
"""Huawei kernel.img (boot image v0, kernel only) packer.

Header fields (kernel/tags address, page size, name) are taken from a template kernel.img.
The cmdline is copied from the template; replace it with --cmdline or extend it with --append-cmdline.

Usage:
  kernel_pack.py TEMPLATE_kernel.img Image.gz-dtb OUT.img [--cmdline "..."] [--append-cmdline "..."]
"""
import argparse
import hashlib
import struct

ap = argparse.ArgumentParser()
ap.add_argument("template")
ap.add_argument("kernel")
ap.add_argument("out")
ap.add_argument("--cmdline")
ap.add_argument("--append-cmdline", default="")
a = ap.parse_args()

tpl = open(a.template, "rb").read()
assert tpl[:8] == b"ANDROID!"
ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack_from("<8I", tpl, 8)
assert rs == 0 and ss == 0, "expected a kernel-only template"
k = open(a.kernel, "rb").read()

hdr = bytearray(tpl[:ps])
struct.pack_into("<I", hdr, 8, len(k))
cmd = bytes(hdr[64:576]).split(b"\0")[0].decode()
if a.cmdline is not None:
    cmd = a.cmdline
if a.append_cmdline:
    cmd = (cmd + " " + a.append_cmdline).strip()
assert len(cmd) < 512, "cmdline exceeds 512 bytes"
hdr[64:576] = cmd.encode().ljust(512, b"\0")
hdr[608:1632] = b"\0" * 1024  # extra cmdline empty
sha = hashlib.sha1()
for blob in (k, b"", b""):
    sha.update(blob)
    sha.update(struct.pack("<I", len(blob)))
hdr[576:608] = sha.digest().ljust(32, b"\0")
open(a.out, "wb").write(bytes(hdr) + k + b"\0" * ((-len(k)) % ps))
print(f"{a.out}: kernel {len(k)} bytes\ncmdline: {cmd}")
