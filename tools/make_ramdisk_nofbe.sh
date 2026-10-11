#!/bin/bash
# Build the ramdisk for this ROM from YOUR stock firmware (the stock ramdisk contains Huawei's init and is not
# redistributed). The only change: an fstab without file-based encryption, bind-mounted over the vendor fstab —
# Android 10's vold cannot set up FBE keys with the Android 8.0 init (no fscrypt keyring).
# Part of android_huawei_atu_l21/tools (uses huawei_app.py and ramdisk_add.py next to it).
# Usage: tools/make_ramdisk_nofbe.sh <UPDATE.APP> [out.img]   (needs python3, simg2img, debugfs)
set -eu
APP=$(readlink -f "${1:?UPDATE.APP}"); T=$(cd "$(dirname "$0")" && pwd); OUT=$(readlink -f "${2:-atu_l21-ramdisk-a10-nofbe.img}")
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT; cd "$D"
python3 "$T/huawei_app.py" extract "$APP" stock RAMDISK
# The vendor fstab is not in the ramdisk: take it from the stock vendor image
python3 "$T/huawei_app.py" extract "$APP" stock VENDOR
simg2img stock/vendor.img vendor.raw
debugfs -R 'dump /etc/fstab.qcom fstab.stock' vendor.raw 2>/dev/null
[ -s fstab.stock ] || { echo "fstab.qcom not found in the vendor image"; exit 1; }
sed 's/,fileencryption=[^, ]*//' fstab.stock > fstab.nofbe
grep -q fileencryption fstab.nofbe && { echo "fileencryption still present"; exit 1; }
cat > init.qcom.rc <<'RC'
# ATU-L21: Android 10 vold cannot set up FBE with the 8.0 init (no fscrypt keyring) -> mount /data unencrypted.
on init
    mount none /fstab.nofbe /vendor/etc/fstab.qcom bind
RC
python3 "$T/ramdisk_add.py" stock/ramdisk.img "$OUT" fstab.nofbe:./fstab.nofbe:0640 init.qcom.rc:./init.qcom.rc:0750
sha256sum "$OUT"
