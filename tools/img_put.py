#!/usr/bin/env python3
"""Puts files into a raw ext4 system image (via debugfs), sets SELinux label/mode/owner
and verifies the result by comparing contents.

Usage:
  img_put.py IMAGE LOCAL:TARGET:MODE:UID:GID:SELINUX_CTX [...]
  e.g.: img_put.py v416-dbg.raw out/libx.so:/system/lib64/libx.so:0644:0:0:u:object_r:system_lib_file:s0
Note: the context contains ':', so fields are split 5 times from the left.
"""
import os
import subprocess
import sys
import tempfile


def dbg(img, cmds, write=False):
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".cmd") as f:
        f.write("\n".join(cmds) + "\n")
        name = f.name
    args = ["debugfs"] + (["-w"] if write else []) + ["-f", name, img]
    r = subprocess.run(args, capture_output=True, text=True)
    os.unlink(name)
    return r.stdout + r.stderr


def exists(img, path):
    return "Inode:" in dbg(img, [f"stat {path}"])


def main():
    img = sys.argv[1]
    tmp = tempfile.mkdtemp()
    ok = True
    for spec in sys.argv[2:]:
        local, target, mode, uid, gid, ctx = spec.split(":", 5)
        ctxf = os.path.join(tmp, "ctx")
        open(ctxf, "wb").write(ctx.encode() + b"\0")
        cmds = []
        if exists(img, target):
            cmds.append(f"unlink {target}")
        cmds += [f"write {local} {target}",
                 f"sif {target} mode 0100{mode[-3:]}",
                 f"sif {target} uid {uid}",
                 f"sif {target} gid {gid}",
                 f"ea_set -f {ctxf} {target} security.selinux"]
        dbg(img, cmds, write=True)
        chk = os.path.join(tmp, "chk")
        dbg(img, [f"dump {target} {chk}"])
        same = os.path.exists(chk) and open(chk, "rb").read() == open(local, "rb").read()
        label = ctx in dbg(img, [f"ea_list {target}"])
        print(f"{'OK  ' if same and label else 'FAIL'} {target}")
        ok &= same and label
        if os.path.exists(chk):
            os.unlink(chk)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
