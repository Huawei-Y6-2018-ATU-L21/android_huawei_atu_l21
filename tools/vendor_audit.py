#!/usr/bin/env python3
"""ATU-L21 vendor audit: static compatibility of 8.0 vendor/odm ELFs with the Android 12 system.

Usage:
  vendor_audit.py ROOT [--json out.json] [--md out.md]
ROOT contains: vendor/, odm/ (from the device), sys/lib, sys/lib64, sys/apex/<name>/lib{,64} (Android 12).

Checks (per ELF):
  1. NEEDED resolution — with the legacy linker search order of vendor processes
     (/system -> /vendor -> /odm; bionic from the runtime APEX).
  2. Unresolved GLOBAL symbols (against the dependency closure).
  3. ABI risk: code that constructs system classes whose size/layout changed since 8.0
     (e.g. android::Parcel allocated on the stack with the 8.0 size -> the Android 12 constructor overflows).
"""
import argparse
import collections
import json
import os
import subprocess
import sys

from elftools.common.exceptions import ELFError
from elftools.elf.dynamic import DynamicSection
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

# Constructors of classes whose size changed between 8.0 and 12. If vendor code constructs them
# itself (stack/new) the memory layout does not match. Extend the list as needed.
ABI_HAZARD_CTORS = {
    "_ZN7android6ParcelC1Ev": "android::Parcel (8.0: 104 B, 12: 120 B @64-bit)",
    "_ZN7android6ParcelC2Ev": "android::Parcel (8.0: 104 B, 12: 120 B @64-bit)",
}

# Symbols provided by the linker/bionic itself or always assumed present.
ALWAYS = {"__cxa_finalize", "__cxa_atexit", "__register_atfork", "__libc_init", "__stack_chk_fail",
          "__stack_chk_guard", "dl_iterate_phdr", "__sF", "__progname", "environ", "_DYNAMIC"}


def parse(path):
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"\x7fELF":
                return None
            f.seek(0)
            e = ELFFile(f)
            info = {"bits": e.elfclass, "type": e["e_type"], "needed": [], "soname": None,
                    "defs": set(), "undefs": set()}
            for sec in e.iter_sections():
                if isinstance(sec, DynamicSection):
                    for t in sec.iter_tags():
                        if t.entry.d_tag == "DT_NEEDED":
                            info["needed"].append(t.needed)
                        elif t.entry.d_tag == "DT_SONAME":
                            info["soname"] = t.soname
                elif isinstance(sec, SymbolTableSection) and sec.name == ".dynsym":
                    for s in sec.iter_symbols():
                        if not s.name:
                            continue
                        b = s["st_info"]["bind"]
                        if s["st_shndx"] == "SHN_UNDEF":
                            if b == "STB_GLOBAL":
                                info["undefs"].add(s.name)
                        elif b in ("STB_GLOBAL", "STB_WEAK", "STB_GNU_UNIQUE"):
                            info["defs"].add(s.name.split("@")[0])
            return info
    except (ELFError, OSError, ValueError, KeyError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args()
    R = a.root

    def search_dirs(lib):  # lib = "lib" | "lib64"
        dirs = [f"{R}/sys/apex/com.android.runtime/{lib}/bionic", f"{R}/sys/{lib}",
                f"{R}/vendor/{lib}", f"{R}/vendor/{lib}/egl", f"{R}/odm/{lib}"]
        for ap_ in sorted(os.listdir(f"{R}/sys/apex")):
            dirs.append(f"{R}/sys/apex/{ap_}/{lib}")
        return [d for d in dirs if os.path.isdir(d)]

    cache = {}

    def info_of(path):
        if path not in cache:
            cache[path] = parse(path)
        return cache[path]

    def resolve(name, lib):
        for d in search_dirs(lib):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        return None

    targets = []
    for base in ("vendor", "odm"):
        for dp, dn, fn in os.walk(os.path.join(R, base)):
            if "/app/" in dp + "/" or "/priv-app/" in dp + "/" or "/framework" in dp:
                continue
            for f in fn:
                p = os.path.join(dp, f)
                if os.path.islink(p):
                    continue
                i = info_of(p)
                if i and i["type"] in ("ET_EXEC", "ET_DYN"):
                    targets.append(p)

    results = {}
    for n, p in enumerate(sorted(targets)):
        i = info_of(p)
        lib = "lib64" if i["bits"] == 64 else "lib"
        missing_libs, seen, queue, defs = [], set(), list(i["needed"]), set(i["defs"])
        while queue:
            name = queue.pop(0)
            if name in seen:
                continue
            seen.add(name)
            q = resolve(name, lib)
            if not q:
                missing_libs.append(name)
                continue
            qi = info_of(q)
            if qi:
                defs |= qi["defs"]
                queue += qi["needed"]
        missing_syms = sorted(s for s in i["undefs"] - defs - ALWAYS)
        hazards = sorted({ABI_HAZARD_CTORS[s] for s in i["undefs"] if s in ABI_HAZARD_CTORS})
        if missing_libs or missing_syms or hazards:
            results[os.path.relpath(p, R)] = {"bits": i["bits"], "missing_libs": missing_libs,
                                              "missing_syms": missing_syms, "abi_hazards": hazards}
        if n % 500 == 0:
            print(f"  {n}/{len(targets)}", file=sys.stderr)

    if a.json:
        json.dump(results, open(a.json, "w"), indent=1, ensure_ascii=False)

    # Summary
    lib_counter = collections.Counter(l for r in results.values() for l in r["missing_libs"])
    sym_counter = collections.Counter(s for r in results.values() for s in r["missing_syms"])
    haz = [(k, r) for k, r in results.items() if r["abi_hazards"]]

    def dem(names):
        out = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True).stdout
        return out.splitlines()

    lines = [f"# Vendor audit (static)\n", f"- ELFs scanned: {len(targets)}",
             f"- ELFs with issues: {len(results)}",
             f"- With missing libraries: {sum(1 for r in results.values() if r['missing_libs'])}",
             f"- With unresolved symbols: {sum(1 for r in results.values() if r['missing_syms'])}",
             f"- ABI risk (Parcel etc.): {len(haz)}\n",
             "## Most frequently missing libraries", ""]
    for l, c in lib_counter.most_common(40):
        lines.append(f"- `{l}` — {c} ELFs")
    lines += ["", "## Most frequently missing symbols", ""]
    top = sym_counter.most_common(60)
    for (s, c), d in zip(top, dem([s for s, _ in top])):
        lines.append(f"- {c:4d} × `{d[:140]}`")
    lines += ["", "## ELFs with an ABI risk", ""]
    for k, r in sorted(haz):
        lines.append(f"- `{k}` ({r['bits']}-bit): {', '.join(r['abi_hazards'])}")
    if a.md:
        open(a.md, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
