# LineageOS 17.1 (Android 10) for ATU-L21 — unofficial

A second, much simpler ROM next to the Android 12 build: **LineageOS 17.1** on the phone's stock Android 8.0
vendor, with the **stock 8.0 ramdisk** (only file-based encryption disabled) instead of a new first-stage init.
Not affiliated with or endorsed by the LineageOS project.

| | |
|---|---|
| Android | 10 (LineageOS 17.1, security patch level of the LineageOS tree at build time) |
| Base | LineageOS 17.1 + phh treble (A-only arm64, AndyYan's `lineage_build_unified` steps) |
| Flavour | vanilla: no Google services, F-Droid installed on first boot. GApps: see below |
| Kernel | the same 3.18.140 kernel as the Android 12 build |
| Build type | `userdebug`, SELinux **enforcing** |
| Sources | [atu_l21_patches `lineage-17.1`](https://github.com/Huawei-Y6-2018-ATU-L21/atu_l21_patches/tree/lineage-17.1), [device](https://github.com/Huawei-Y6-2018-ATU-L21/android_device_huawei_atu_l21/tree/lineage-17.1), [vendor](https://github.com/Huawei-Y6-2018-ATU-L21/android_vendor_atu/tree/lineage-17.1) |

## Why it needs so little

Android 9 GSIs already ran on this phone; Android 10 failed only because its `vold` expects the `fscrypt` keyring that
the Android 8.0 init does not create (see [HISTORY.md](HISTORY.md), attempts 2 and 3). With encryption disabled in
the ramdisk, Android 10 boots on the stock init. What was still needed:

| Problem | Fix |
|---|---|
| Android 10 `vold` cannot set up file-based encryption with the 8.0 init | ramdisk: an fstab without `fileencryption` bind-mounted over the vendor fstab (`/data` unencrypted) |
| The Huawei-modified 8.0 init **never reads `/system/build.prop`** — model, LineageOS version, all system properties were missing (`Android/msm8937_64/...:10/unknown/unknown` fingerprint) | build/make appends build.prop to `/system/etc/prop.default`, which it does read, and derives `ro.build.fingerprint` |
| 8.0 vendor binaries allocate `android::Parcel` on the stack with the 8.0 size (104 B, Android 10: 120 B) | Parcel flags packed so the size matches 8.0 — same fix as the Android 12 build ([PATCHES.md §2](PATCHES.md)) |
| `gpuservice` restart loop: the 8.0 init does not know the `gpu_service` user | numeric UID 1072 in its rc file |
| `llkd` (debuggable builds) can panic the kernel on a suspected live-lock | disabled (`ro.llk.enable=false`, `ro.khungtask.enable=false`) |
| `/vendor/build.prop` is loaded after the system's properties and sets heap sizes for 3 GB | Go values set again from an init rc before zygote starts |
| phh's "Phh Treble Settings" app and overlays for ~340 other phones | not installed; only the 6 overlays active on ATU-L21 (phh's ATU overlay brings GPS settings, the auto-brightness curve and the power profile) |

## What works

Tested by the maintainers: display, touch, auto-brightness, Wi-Fi, Bluetooth, both cameras, modem/baseband,
sensors, audio, video playback, WebView 154, F-Droid, GApps (MindTheGapps). No problems were seen in daily use.
Reports about calls/SMS/mobile data with a SIM are very welcome.

Known: Huawei's display-engine HAL restarts in a loop (SELinux; no visible effect), `netd` crashes once at boot.

## Install

You need an unlocked bootloader and TWRP in `recovery_ramdisk` — see [FLASHING.md](FLASHING.md) for the phone modes
and the general warnings (never relock the bootloader).

**1. Build the ramdisk from your stock firmware.** The stock ramdisk contains Huawei's init and is not
redistributed. With the 8.0.0.133 C432 `UPDATE.APP`:

```bash
tools/make_ramdisk_nofbe.sh UPDATE.APP atu_l21-ramdisk-a10-nofbe.img   # python3, simg2img, debugfs
# C432 8.0.0.133 -> sha256 49f7346a4f0b148beacdffe5aa49d5fe29b6c2ac748340ec8eabc2a4f2f67b0f
```

**2. Format userdata in TWRP** (the phone was encrypted or ran another ROM):

```bash
adb reboot recovery
adb shell 'for m in $(grep mmcblk0p55 /proc/mounts | cut -d" " -f2); do umount -l $m; done'
adb shell mkfs.f2fs -t 0 /dev/block/mmcblk0p55
```

**3. Flash in fastboot** (`adb reboot bootloader` from TWRP):

```bash
xz -dk lineage-17.1-20261011-UNOFFICIAL-atu_l21.img.xz
fastboot flash system  lineage-17.1-20261011-UNOFFICIAL-atu_l21.img
fastboot flash kernel  atu_l21-kernel-3.18.140-atu.img
fastboot flash ramdisk atu_l21-ramdisk-a10-nofbe.img
fastboot reboot
```

If the phone starts TWRP instead of Android, run `adb reboot` from TWRP.

## GApps (optional)

Google's apps may not be redistributed, so they are not part of the image. MindTheGapps works, but its installer
assumes the system-as-root layout (`/mnt/system/system`) and aborts on this A-only phone. `tools/patch_gapps_aonly.py`
changes only that line of the installer (and keeps it from mounting Huawei's `product` partition read-write):

```bash
# MindTheGapps-10.0.0-arm64-*.zip from https://github.com/MindTheGapps/10.0.0-arm64/releases
python3 tools/patch_gapps_aonly.py MindTheGapps-10.0.0-arm64-20230922_081111.zip
adb reboot recovery                      # after step 3, before the first boot
adb push MindTheGapps-10.0.0-arm64-20230922_081111-aonly.zip /tmp/gapps.zip
adb shell twrp install /tmp/gapps.zip
# if Android was already started once: format userdata again (step 2) before rebooting
adb reboot
```

## Notes

- TWRP 3.2.3 mounts `vendor` and `version` read-write whenever it starts; dm-verity's error correction repairs the
  changed superblock at the next boot (`soft hash fail, fec correct success` in the kernel log). Harmless.
- Root: none included; Magisk can be added by the user.
- The LineageOS updater cannot find updates for this unofficial build; new versions are published here.
