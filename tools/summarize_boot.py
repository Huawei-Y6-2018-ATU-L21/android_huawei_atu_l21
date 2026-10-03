#!/usr/bin/env python3
"""Summarizes pull_pstore.py output: crashing services, linker errors, abort messages."""
import collections, re, sys
d = sys.argv[1]
t = open(f"{d}/console.txt", "rb").read().decode(errors="replace").splitlines()
lc = open(f"{d}/logcat-pmsg.txt", errors="replace").read().splitlines()
c = collections.Counter()
for l in t:
    m = re.search(r"init: Service '([^']+)' \(pid \d+\) (exited with status \d+|received signal \d+)", l)
    if m and not m.group(1).startswith("exec "):
        c[(m.group(1)[:50], m.group(2))] += 1
print("== Crashed/exited services"); [print(" ", v, k) for k, v in c.most_common(20)]
cl = collections.Counter(re.sub(r"^.*?(CANNOT LINK|cannot locate)", r"\1", l)[:220] for l in t
                         if re.search("CANNOT LINK|cannot locate symbol", l))
print("== Linker errors"); [print(" ", v, k) for k, v in cl.most_common(15)]
ab = collections.Counter()
for i, l in enumerate(lc):
    if "Abort message" in l:
        cmd = next((x for x in lc[max(0, i - 12):i] if "Cmdline:" in x), "")
        ab[(cmd.split("Cmdline:")[-1].strip()[:60], l.split("Abort message:")[-1].strip()[:120])] += 1
print("== Abort messages"); [print(" ", v, k) for k, v in ab.most_common(12)]
print("== Last init lines"); [print(" ", x[:200]) for x in [l for l in t if "[1, init]" in l][-8:]]
print("== boot_completed / zygote / surfaceflinger:")
for k in ("sys.boot_completed", "starting service 'zygote'", "starting service 'surfaceflinger'", "bootanim"):
    print(f"  {k}: {sum(k in l for l in t)}")
