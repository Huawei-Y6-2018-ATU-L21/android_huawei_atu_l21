#!/usr/bin/env python3
"""Finds unresolved symbols of vendor ELFs (against Android 12 system + vendor/odm libraries).

Usage: vendor_symcheck.py TMPDIR   (TMPDIR/{v,odm,s/lib,s/lib64} rdump output)
Output: missing symbol -> binaries using it (per architecture), summary.
"""
import collections
import os
import subprocess
import sys

root = sys.argv[1]


def elf_class(path):
    with open(path, "rb") as f:
        h = f.read(5)
    if h[:4] != b"\x7fELF":
        return None
    return "lib64" if h[4] == 2 else "lib"


def nm(path, defined):
    args = ["nm", "-D", "--defined-only" if defined else "--undefined-only", path]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    syms = set()
    for line in out.splitlines():
        p = line.split()
        if not p:
            continue
        if defined and len(p) >= 3:
            syms.add(p[2].split("@")[0])
        elif not defined:
            if p[0] in ("w", "v"):  # weak: not required
                continue
            syms.add(p[-1].split("@")[0])
    return syms


provided = {"lib": set(), "lib64": set()}
elfs = []
for base in ("s", "v", "odm"):
    for dp, dn, fn in os.walk(os.path.join(root, base)):
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.islink(p):
                continue
            try:
                c = elf_class(p)
            except OSError:
                continue
            if not c:
                continue
            if f.endswith(".so"):
                provided[c] |= nm(p, True)
            if base != "s":
                elfs.append((c, p))

# bionic/ld symbols
for c in provided:
    provided[c] |= {"__cxa_finalize", "__cxa_atexit", "__register_atfork", "__libc_init",
                    "__stack_chk_fail", "__stack_chk_guard", "dl_iterate_phdr"}

missing = collections.defaultdict(set)
for c, p in elfs:
    for s in nm(p, False) - provided[c]:
        missing[(c, s)].add(os.path.relpath(p, root))

by_bin = collections.defaultdict(list)
for (c, s), users in missing.items():
    for u in users:
        by_bin[u].append(s)

for u in sorted(by_bin, key=lambda x: -len(by_bin[x])):
    syms = sorted(by_bin[u])
    dem = subprocess.run(["c++filt"], input="\n".join(syms), capture_output=True, text=True).stdout
    print(f"## {u} ({len(syms)})")
    for d in dem.splitlines()[:8]:
        print("   ", d[:160])
print(f"\nTotal: {len(by_bin)} binaries, {len(missing)} (arch, symbol) missing")
