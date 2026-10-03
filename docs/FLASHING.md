# Installing

> **Read everything first.** Userdata is erased. You need an **unlocked bootloader** and **TWRP** in
> `recovery_ramdisk` (TWRP 3.2.3 for ATU-L21 works). **Never relock the bootloader** (`fastboot oem relock`,
> `fastboot flashing lock`) while custom software is installed — that can brick the phone permanently.
> Never flash anything other than `system`, `kernel`, `ramdisk`, `recovery_ramdisk` and `userdata`.

## What you need

- Stock firmware **8.0 (EMUI 8)** on the phone — the ROM uses the stock vendor/odm partitions unchanged.
- `adb` and `fastboot` (platform-tools).
- From the [release](../../../releases): one system image, the kernel and the ramdisk. Check `SHA256SUMS`.
- The stock `UPDATE.APP` for your region to go back (see the end of this page).

```bash
xz -dk atu_l21-v10.img.xz        # -> atu_l21-v10.img (2624 MiB raw ext4)
sha256sum -c SHA256SUMS
```

## Phone modes

| Mode | How |
|---|---|
| fastboot | phone off, USB connected: **Volume Down + Power**, or `adb reboot bootloader` |
| TWRP | phone off, USB **disconnected**: **Volume Up + Power**, or `adb reboot recovery` |

`fastboot reboot recovery` boots the normal system on this phone — don't rely on it.

## Steps

### 1. Flash in fastboot

```bash
fastboot devices
fastboot flash system  atu_l21-v10.img              # or atu_l21_microg-v10.img
fastboot flash kernel  atu_l21-kernel-3.18.140-atu.img
fastboot flash ramdisk atu_l21-ramdisk-a12-2si.img
```

fastboot splits the raw image automatically (max-download-size is 511 MB). Do **not** use `fastboot -w`
or `fastboot format userdata`: fastboot thinks userdata is ext4, it is f2fs.

### 2. Format userdata in TWRP

Boot to TWRP (Volume Up + Power with the cable unplugged, then plug it back in). TWRP 3.2.3 hangs on
Android 12's binary (ABX) XML files with *Format Data*, so format from the shell:

```bash
adb shell 'for m in $(grep mmcblk0p55 /proc/mounts | cut -d" " -f2); do umount -l $m; done'
adb shell mkfs.f2fs -t 0 /dev/block/mmcblk0p55
```

`mmcblk0p55` is `userdata` on ATU-L21 — check it on your phone first:
`adb shell ls -l /dev/block/bootdevice/by-name/userdata`.

A wipe is required when coming from stock or another ROM. Updating between versions of this ROM works
without it in most cases; if something misbehaves, format.

### 3. Boot

```bash
adb reboot
```

The first boot takes about 1 minute (dex2oat). The vanilla build installs F-Droid shortly after the first boot.

## Trouble

| Symptom | Fix |
|---|---|
| Every boot ends in TWRP | The `misc` partition holds a leftover Huawei `boot-recovery --usb_update` command (often after an eRecovery visit). In TWRP: `adb shell dd if=/dev/zero of=/dev/block/bootdevice/by-name/misc bs=2048 count=1` — this clears only the bootloader message block (first 2 KiB). |
| Huawei eRecovery appears | Do **not** choose *factory reset* or *download latest version*. Reboot and enter TWRP with the key combination. |
| Boot logo, then reboot to TWRP after ~3 min | init hit a fatal error; logs are in `/cache/init-fatal/` and pstore — see [DEBUGGING.md](DEBUGGING.md). |
| Boot animation forever | userdata not formatted. |

## Back to stock

Extract the stock images with `tools/huawei_app.py` and flash the parts this ROM changed:

```bash
python3 tools/huawei_app.py extract UPDATE.APP stock/ SYSTEM KERNEL RAMDISK
fastboot flash system  stock/system.img
fastboot flash kernel  stock/kernel.img
fastboot flash ramdisk stock/ramdisk.img
```

Then format userdata in TWRP as above (stock uses f2fs + file-based encryption, which Android sets up again on
the first boot).

**Last resort** (no fastboot, bootloop you cannot fix): Huawei *dload*. Copy `UPDATE.APP` (and the region
`update_*_hw_*.app` cust package) into `dload/` on a FAT32 SD card, then hold **Volume Up + Volume Down + Power**
with the phone off. This writes the whole official firmware (including the stock recovery — reinstall TWRP
afterwards with `fastboot flash recovery_ramdisk twrp.img`).
