# How it works

## The device

| Property | Value |
|---|---|
| Model / board | ATU-L21 / ATU-L01, firmware C432 (`System 8.0.0.063`) |
| SoC | Qualcomm MSM8917 (`ro.board.platform=msm8937`), 4× Cortex-A53, Adreno 308, 2 GB RAM |
| Partition scheme | **A-only**, **not** system-as-root; Treble enabled (`ro.treble.enabled=true`) |
| Binder | 64-bit binder; `binder`, `hwbinder`, `vndbinder` |
| Vendor | Android 8.0 (API 26), **no `ro.vndk.version`**, no VNDK APEX — vendor binaries link `/system` libraries directly |
| Kernel | stock 3.18.66; this build uses 3.18.140 (pascua28 tree) |
| Encryption | stock: FBE; this build disables it (see PATCHES) |
| Userdata | **f2fs** (fastboot wrongly reports ext4 — never use `fastboot -w`) |

### Huawei split boot

There is no `boot` partition. The bootloader (Qualcomm LK, Huawei-modified) loads two separate Android
boot images (header v0):

| Partition | Block | Content |
|---|---|---|
| `kernel` | mmcblk0p41 | kernel + appended DTBs, **kernel cmdline is taken from this header** |
| `ramdisk` | mmcblk0p42 | ramdisk only (gzip cpio); its header cmdline is **ignored** |
| `recovery_ramdisk` | mmcblk0p43 | recovery ramdisk (TWRP) |
| `system` | mmcblk0p54 | 0xa4000000 bytes (2624 MiB) |
| `userdata` | mmcblk0p55 | ~10.2 GiB, f2fs |

`tools/kernel_pack.py` and `tools/ramdisk_replace.py` build images in this format from the stock headers.

## Why Android 12 does not "just boot"

phh-treble stopped publishing A-only images after Android 11 (v313). The Android 12 v416 GSI is
**system-as-root (SAR) only**. On an A-only, non-SAR device the bootloader starts `/init` from the
ramdisk partition, which on stock is the Android 8.0 init — it cannot boot an Android 12 system.

Android 10 introduced *Two-Stage Init* (2SI), which solves exactly this:

```
LK ──► kernel ──► /init (ramdisk: Android 12 first-stage init)
                     │  reads the fstab from the device tree (system, vendor, odm)
                     │  mounts system at /system, then switch_root to it
                     ▼
                  /system/bin/init (second stage, from the Android 12 system image)
                     │  SELinux: plat policy (12) + vendor policy (8.0)
                     ▼
                  init.rc ─► vendor init.qcom.rc, HALs, zygote, system_server
```

So the build ships its own **ramdisk** that contains only the Android 12 first-stage init and the
directory skeleton (AOSP `ramdisk` target), packed with the stock ramdisk header.

## Android 12 system + Android 8.0 vendor

Treble promises that a newer system works with an older vendor through stable HIDL interfaces. In practice
an 8.0 vendor without VNDK breaks that promise in many places, because its binaries still link and call
**system** libraries directly. Every incompatibility falls into one of these classes:

| Class | Example | Where fixed |
|---|---|---|
| Removed library | `libmediacodecservice.so` (OMX) | system-side rebuild of the service |
| Removed / moved symbol | `android::base::LogMessage` old constructor, HIDL `toString`, `android::HidlUtils` | `libbase`, `libatu_shim`, audio util |
| Changed struct size (ABI) | **`android::Parcel` 104 → 120 bytes** | `Parcel.h` packing |
| Changed struct layout | `audio_port_config`, `audio_offload_info_t` | legacy `HidlUtils` with 8.0 layouts |
| Linker config | no VNDK version → "legacy" linkerconfig; APEX processes cannot see `/system/lib` | `linkerconfig` |
| File locations | firmware in `/odm/etc/firmware`, `/vendor/ueventd.rc` | `ueventd` |
| Stricter parsing | 8.0 `media_codecs_performance.xml` | codec list builders |
| Properties | vendor overrides `ro.build.*` with 8.0 values | `property_service` |
| Kernel (3.18) | no cgroup2, no eBPF, no PSI, not in the Android 12 kernel matrix | fallbacks in init/libprocessgroup, lmkd props, VINTF check |
| Driver behaviour | Adreno 308 slow GMEM resolves, SDM HWC layer limit | RenderEngine hint, overlays |

The linker runs vendor processes in the **legacy** linkerconfig section: no namespace isolation, search order
`/system → /system_ext → /product → /vendor → /odm (+ /vendor/lib/hw)`. A dedicated `legacy_vendor` section
prepends `/system/${LIB}/atu-compat` for the few processes that need Android 9 protobuf (RIL, Widevine,
audio HAL). Note that phh's `vndk.rc` sets `ro.vndk.version=26` *after* linkerconfig has run at boot;
running `linkerconfig` by hand later produces a completely different (VNDK) configuration — never do that.

Every change and the reasoning behind it: [PATCHES.md](PATCHES.md).

## Kernel command line

Set in the kernel image header (`tools/kernel_pack.py --cmdline`):

```
androidboot.hardware=qcom msm_rtb.filter=0x237 ehci-hcd.park=3 lpm_levels.sleep_disabled=1
androidboot.bootdevice=7824900.sdhci slub_min_objects=12 unmovable_isolate1=2:192M,3:224M,4:256M
unmovable_isolate2=2:64M,3:80M,4:80M androidboot.selinux=permissive
ramoops.mem_address=0x8f100000 ramoops.mem_size=0x400000 ramoops.console_size=0x200000
ramoops.pmsg_size=0x100000 ramoops.record_size=0x40000 androidboot.init_fatal_reboot_target=recovery
```

The `ramoops.*` parameters reserve 4 MiB at 0x8f100000 for pstore, so kernel and logcat output of a
failed boot can be read from TWRP (`/sys/fs/pstore`). See [DEBUGGING.md](DEBUGGING.md).

## Huawei specifics to know

- **BFM (boot fail monitor)** reboots into eRecovery if the system does not report "boot success" within
  ~10 minutes. Non-EMUI systems never report it → patched in the kernel.
- After an eRecovery boot the **misc** partition may keep a `boot-recovery --usb_update` command, making
  every boot go to recovery. Clearing the bootloader message block fixes it (see FLASHING).
- `fastboot reboot recovery` boots the normal system; use `adb reboot recovery` or
  Volume Up + Power.
- Never relock the bootloader with custom software installed.
