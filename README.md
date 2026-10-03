# Android 12 for the Huawei Y6 2018 (ATU-L21)

An Android 12 (12.1, API 32) build for the **Huawei Y6 2018 — ATU-L21** (Qualcomm MSM8917, 2 GB RAM),
running on the phone's **stock Android 8.0 (EMUI 8) vendor** and a **3.18 kernel**.
The phone was never meant to run anything newer than Android 8.0: no Treble GSI newer than Android 10 boots
on it out of the box. This project documents every change that was needed and why, so that others can
reproduce, audit and improve it.

| | |
|---|---|
| Android | 12.1 (phh-treble v416 base, AOSP `android-12.1.0_r11`), Go/low-RAM tuned |
| Flavours | **vanilla** (no Google services, F-Droid) and **microG** (signature spoofing, Aurora Store) |
| Browser / WebView | Jelly (LineageOS) / Chromium WebView 154 |
| Kernel | 3.18.140 ([android_kernel_huawei_atu_l21](https://github.com/Huawei-Y6-2018-ATU-L21/android_kernel_huawei_atu_l21)) |
| Build type | `userdebug`, SELinux **permissive** |
| Status | daily-usable; see [what works](#what-works) |

## Downloads

Get the images from the [Releases](../../releases) page:

| File | Flash to |
|---|---|
| `atu_l21-v10.img.xz` *(vanilla)* or `atu_l21_microg-v10.img.xz` *(microG)* | `system` (decompress first) |
| `atu_l21-kernel-3.18.140-atu.img` | `kernel` |
| `atu_l21-ramdisk-a12-2si.img` | `ramdisk` |

Installation: [docs/FLASHING.md](docs/FLASHING.md). **Back up everything you need — userdata must be formatted.**

## What works

| Feature | State | Notes |
|---|---|---|
| Display, touch, brightness | ✅ | Home screen ~57 FPS, Settings ~56 FPS |
| Wi-Fi | ✅ | |
| Audio (speaker, headset) | ✅ | TFA9872 amplifier firmware loaded from `/odm/etc/firmware` |
| Bluetooth | ✅ | discover/pair verified |
| Camera (rear + front) | ✅ | |
| Hardware video decoding | ✅ | H.264, HEVC, VP8 via Qualcomm OMX; VP9/AV1 in software (no hardware support on MSM8917) |
| Modem / RIL | ✅* | modem boots, RIL reports baseband and both SIM slots; **calls/SMS/data not yet tested with a SIM** |
| Sensors, GPS service | ✅ | GPS fix not yet tested outdoors |
| Widevine | ✅* | service runs and reports support (L3 expected); not tested with a streaming app |
| microG | ✅ | signature spoofing passes microG self-check |
| Fingerprint | — | the ATU-L21 has no fingerprint sensor |
| SELinux enforcing | ❌ | permissive only (vendor policy is 8.0) |
| Root | — | not included; Magisk planned |

Details: [docs/KNOWN-ISSUES.md](docs/KNOWN-ISSUES.md).

## Documentation

| Document | Content |
|---|---|
| [HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md) | Boot chain, partitions, how an 8.0 vendor and Android 12 coexist |
| [BUILDING.md](docs/BUILDING.md) | Build the ROM, ramdisk and kernel from source |
| [FLASHING.md](docs/FLASHING.md) | Install, wipe, recover back to stock |
| [PATCHES.md](docs/PATCHES.md) | **Every change: symptom → root cause → fix → verification** |
| [DEBUGGING.md](docs/DEBUGGING.md) | Techniques used: pstore, logcat, stack sampling, small on-device test programs |
| [VENDOR-AUDIT.md](docs/VENDOR-AUDIT.md) | Static audit of all 4816 vendor ELFs against Android 12 |
| [HISTORY.md](docs/HISTORY.md) | How the port progressed (GSIs tried, versions v1–v10) |
| [KNOWN-ISSUES.md](docs/KNOWN-ISSUES.md) | Open problems and workarounds |

## Repositories

| Repository | Goes to |
|---|---|
| [android_huawei_atu_l21](https://github.com/Huawei-Y6-2018-ATU-L21/android_huawei_atu_l21) | this guide, tools, releases |
| [atu_l21_patches](https://github.com/Huawei-Y6-2018-ATU-L21/atu_l21_patches) | patches for the AOSP tree + manifest |
| [android_device_huawei_atu_l21](https://github.com/Huawei-Y6-2018-ATU-L21/android_device_huawei_atu_l21) | `device/atu` |
| [android_vendor_atu](https://github.com/Huawei-Y6-2018-ATU-L21/android_vendor_atu) | `vendor/atu` |
| [android_kernel_huawei_atu_l21](https://github.com/Huawei-Y6-2018-ATU-L21/android_kernel_huawei_atu_l21) | kernel source (branch `atu-l21-a12`) |

## Build scripts and tools

`build/` contains the Docker build environment and the sync/build scripts used in [BUILDING.md](docs/BUILDING.md).
`tools/` contains the small utilities written for this port (Huawei `UPDATE.APP` extractor, Huawei
kernel/ramdisk image packers, ext4 image editor, pstore decoder, vendor audit, on-device test programs).
See [docs/DEBUGGING.md](docs/DEBUGGING.md).

## Credits

- [phhusson / TrebleDroid](https://github.com/phhusson) — the treble GSI base this build stands on
- [pascua28](https://github.com/pascua28/android_kernel_msm8917_ATU) — the 3.18.140 ATU kernel
- [LineageOS](https://lineageos.org) — Jelly browser and the Chromium WebView builds
- [microG](https://microg.org), [Aurora OSS](https://gitlab.com/AuroraOSS), [F-Droid](https://f-droid.org)
- The Android Open Source Project

## License

Documentation, tools and build files: Apache License 2.0. Third-party components keep their own licenses
(kernel: GPL-2.0).

This is an unofficial community project, not affiliated with Huawei, Google, LineageOS or phh.
Flashing custom software can brick your device; you do it at your own risk.
