#!/usr/bin/env python3
"""ATU-L21: adapt a MindTheGapps 10.0.0 zip to this A-only (non system-as-root) ROM.

MindTheGapps mounts the system partition on /mnt/system and copies into /mnt/system/system (system-as-root
layout). On ATU-L21 the partition root *is* /system, so the installer aborts ("package is for Android 10 but your
system is Android  (SDK )"). This changes that line of update-binary and stops it from mounting Huawei's own
"product" partition read-write (dm-verity protected, not used by the ROM); nothing else in the package changes.
The Google apps are not redistributed: download the zip yourself and run this on it.

Usage: patch_gapps_aonly.py MindTheGapps-10.0.0-arm64-<date>.zip   -> writes <name>-aonly.zip next to it
"""
import sys, zipfile

BIN = "META-INF/com/google/android/update-binary"
OLD = 'SYSTEM_OUT="${SYSTEM_MNT}/system"\n'
NEW = ('# ATU-L21: A-only layout (the partition root is /system)\n'
       'if [ -f "${SYSTEM_MNT}/system/build.prop" ]; then SYSTEM_OUT="${SYSTEM_MNT}/system"; '
       'else SYSTEM_OUT="${SYSTEM_MNT}"; fi\n')
# Huawei's own "product" partition (dm-verity, not used by the ROM) must not be mounted read-write.
OLD2 = 'PRODUCT_BLOCK=$(find_block "product")\n'
NEW2 = 'PRODUCT_BLOCK=""  # ATU-L21: never mount Huawei\'s product partition (verity)\n'
# The original JAR signature no longer matches; leave it out (TWRP's zip signature check is off by default).
DROP = {"META-INF/MANIFEST.MF", "META-INF/CERT.SF", "META-INF/CERT.RSA"}

src = sys.argv[1]
dst = src[:-4] + "-aonly.zip"
with zipfile.ZipFile(src) as zin:
    script = zin.read(BIN).decode()
    if script.count(OLD) != 1 or script.count(OLD2) != 1:
        sys.exit("unexpected update-binary (not MindTheGapps 10.0.0?)")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename in DROP:
                continue
            data = script.replace(OLD, NEW).replace(OLD2, NEW2).encode() if info.filename == BIN else zin.read(info)
            zout.writestr(info, data, compress_type=info.compress_type)
print(dst)
