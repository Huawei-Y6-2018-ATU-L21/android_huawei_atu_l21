#!/usr/bin/env python3
"""Adds files to a Huawei ramdisk.img (Android boot image v0, ramdisk only).

Existing cpio entries (important for owner/mode/SELinux) are kept; new entries are added
before the TRAILER. Other header fields (addresses, cmdline) are preserved.
The trailing AVB1 signature block is not added (not needed when unlocked; it would be invalid anyway).

Usage:
  ramdisk_add.py IN.img OUT.img TARGET_PATH:SOURCE_FILE:MODE [...]
  e.g.: ramdisk_add.py ramdisk.img out.img init.qcom.rc:./init.qcom.rc:0750
"""
import gzip
import hashlib
import struct
import sys


def parse_newc(buf):
    off, entries = 0, []
    while True:
        hdr = buf[off:off + 110]
        assert hdr[:6] == b"070701", f"bad cpio magic @ {off}"
        f = [int(hdr[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        namesize, filesize = f[11], f[6]
        name = buf[off + 110:off + 110 + namesize - 1].decode()
        p = off + 110 + namesize
        p += (-p) % 4
        data = buf[p:p + filesize]
        p += filesize
        p += (-p) % 4
        if name == "TRAILER!!!":
            return entries
        entries.append((f, name, data))
        off = p


def newc_entry(ino, mode, name, data, nlink=1):
    nb = name.encode() + b"\0"
    fields = [ino, mode, 0, 0, nlink, 0, len(data), 0, 0, 0, 0, len(nb), 0]
    out = b"070701" + b"".join(b"%08X" % x for x in fields) + nb
    out += b"\0" * ((-len(out)) % 4)
    out += data
    out += b"\0" * ((-len(out)) % 4)
    return out


def main():
    src, dst, adds = sys.argv[1], sys.argv[2], sys.argv[3:]
    img = open(src, "rb").read()
    assert img[:8] == b"ANDROID!"
    ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack_from("<8I", img, 8)
    assert ks == 0 and ss == 0, "expected a ramdisk-only image"
    raw = gzip.decompress(img[ps:ps + rs])
    entries = parse_newc(raw)
    names = {n for _, n, _ in entries}
    out = b""
    max_ino = 0
    for f, name, data in entries:
        max_ino = max(max_ino, f[0])
        nb = name.encode() + b"\0"
        f = list(f)
        f[11] = len(nb)
        e = b"070701" + b"".join(b"%08X" % x for x in f) + nb
        e += b"\0" * ((-len(e)) % 4)
        e += data
        e += b"\0" * ((-len(e)) % 4)
        out += e
    for spec in adds:
        target, srcfile, mode = spec.split(":")
        assert target not in names, f"{target} already exists"
        data = open(srcfile, "rb").read()
        max_ino += 1
        out += newc_entry(max_ino, 0o100000 | int(mode, 8), target, data)
        print(f"added: /{target} ({len(data)} bytes, {mode})")
    out += newc_entry(0, 0, "TRAILER!!!", b"")
    out += b"\0" * ((-len(out)) % 512)
    rd = gzip.compress(out, 9, mtime=0)

    # Header: update the ramdisk size and id (same SHA1 scheme as mkbootimg)
    hdr = bytearray(img[:ps])
    struct.pack_into("<I", hdr, 16, len(rd))
    sha = hashlib.sha1()
    for blob in (b"", rd, b""):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    hdr[576:608] = sha.digest().ljust(32, b"\0")
    body = bytes(hdr) + rd + b"\0" * ((-len(rd)) % ps)
    open(dst, "wb").write(body)
    print(f"{dst}: ramdisk {rs} -> {len(rd)} bytes, total {len(body)} bytes")


if __name__ == "__main__":
    main()
