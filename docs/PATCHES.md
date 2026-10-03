# Patches: symptom → root cause → fix → verification

Base: phh-treble **v416** (AOSP `android-12.1.0_r11`). Patches live in
[atu_l21_patches](https://github.com/Huawei-Y6-2018-ATU-L21/atu_l21_patches); device-side files in
[android_device_huawei_atu_l21](https://github.com/Huawei-Y6-2018-ATU-L21/android_device_huawei_atu_l21).
Every change in the source is marked with an `ATU-L21` comment, so `grep -rn ATU-L21` finds all of them.

The entries are in roughly the order they were found. Each one was triggered by a concrete failure on the
device; nothing was changed "just in case".

---

## 1. Getting Android 12 to boot

### 1.1 Stock 8.0 init cannot start Android 10+ → 2SI ramdisk
- **Symptom:** Android 10 GSIs loop in the boot animation and fall into recovery; Android 12 does not even get that far.
- **Cause:** the `ramdisk` partition contains the stock **8.0 init**. Android 10 `vold` expects the `fscrypt`
  keyring created by a newer init (`Unable to find device keyring`), so FBE keys can not be installed and
  `system_server` crash-loops. On top of that, v416 is a SAR-only image.
- **Fix:** own ramdisk with the Android 12 first-stage init (AOSP `ramdisk` target), packed with the stock
  header (`tools/ramdisk_replace.py`, gzip — the stock kernel has no LZ4 support).
- **Verified:** first stage runs, mounts system and `switch_root`s (debug init, see 1.3).

### 1.2 Kernel: dm-verity loop on odm, BFM reboot after 10 minutes
- **Symptom:** endless `dm-verity hash fail` on odm with the 3.18.140 kernel; later, every boot ends in
  Huawei eRecovery after ~600 s.
- **Cause:** the device tree's early-mount fstab requests `verify` for odm, which does not match the
  odm image; Huawei's boot-fail monitor (`hwbfm`) treats "no EMUI boot-success report" as a failed boot.
- **Fix (kernel):** `msm8917.dtsi`/`msm8937.dtsi`: odm `fsmgr_flags = "wait"`;
  `drivers/hwbfm/bfm/core/bfm_timer.c`: do not call `boot_fail_err()` when the timer expires. Disabling
  `CONFIG_USE_BOOTFAIL_RECOVERY_SOLUTION` entirely is not possible — other drivers call BFM functions.
- **Verified:** uptime > 1 h, no eRecovery.

### 1.3 Debug init (`system/core/init/reboot_utils.cpp`) — *debug only*
- Default fatal reboot target `recovery` (Huawei LK ignores the ramdisk header cmdline); on a fatal error the
  kernel log is dumped to `/cache/init-fatal/` (or `/data`), then init waits 180 s so adb can attach.
- This turned "phone reboots, no idea why" into readable logs. It is still in the release builds and
  harmless on a booting system; it will be made conditional.

### 1.4 `hwservicemanager`: "Failed to acquire SELinux handle"
- **Symptom (from 1.3):** `critical process 'hwservicemanager' exited 4 times` → reboot.
- **Cause:** Android 12 `plat_hwservice_contexts` and the 8.0 Qualcomm `nonplat_hwservice_contexts` both
  define `android.hardware.tetheroffload.{config,control}` with different labels → libselinux rejects the file.
- **Fix:** `system/sepolicy/private/hwservice_contexts`: tetheroffload lines commented out (vendor label wins).
- **Verified:** hwservicemanager stays up.

### 1.5 init / fs_mgr / ueventd adaptations (`system/core`)
| File | Problem | Change |
|---|---|---|
| `fs_mgr/fs_mgr_fstab.cpp` | vendor fstab: system/vendor `verify`, userdata FBE | marker files `/system/etc/atu_disable_verity` and `atu_disable_fbe` make fs_mgr ignore those flags (vendor stays untouched) |
| `fs_mgr/fs_mgr.cpp` | `mount_all` re-mounts vendor/odm (already mounted by first stage); empty `/patch_hw` fails | skip mounted points; non-`/data` mount failures are not fatal |
| `init/init.cpp` | a debug watcher thread stole `SIGCHLD` and hung init | removed |
| `init/ueventd.cpp` | without `ro.product.first_api_level`, `/vendor/ueventd.rc` is not read → wrong `kgsl`/`qseecom` permissions | read legacy paths if the file exists |
| `init/property_service.cpp` | vendor `build.prop` overrides `ro.build.*` with 8.0 values (SDK 26!) | `ro.build.*` keeps the system value |
| `init/service.cpp` | stdio→kmsg for all services broke the zygote fd allowlist | only for `/vendor` and `/odm` binaries |
| `init/subcontext.cpp` | 8.0 vendor has no subcontext → null dereference at shutdown | null check |
| `libprocessgroup/setup/cgroup_map_write.cpp` | 3.18 has no cgroup2 → services cannot be stopped/killed | mount cgroup v1 `cpuacct` at the same path |
| `libcutils/atu_thread_store_compat.cpp` | old vendor code calls `thread_store_get/set` | compatibility implementation |
| `healthd/Android.bp` | system_server needs IHealth 2.x, vendor has only 1.0 | system-side `health@2.0-service` (+ framework manifest fragment) |
| `rootdir/init.rc` | vendor services must be overridable | `atu-overrides.rc` imported first |
| `rootdir/ueventd.rc` | see 4.3 | `firmware_directories /odm/etc/firmware/` |

Plus device-side: root mount points (`/firmware /dsp /cust /version /patch_hw /log`, the 2SI root is read-only),
their file_contexts labels, and adb FunctionFS setup that the 8.0 ramdisk `init.usb.rc` used to do.

### 1.6 Linker configuration (`system/linkerconfig`, `bionic`)
- **Symptom:** `linkerconfig` aborts on undefined variables (no VNDK version); vendor HALs cannot find libraries.
- **Fix:**
  - undefined variables expand to empty, empty library names are dropped, missing VNDK variables defined empty;
  - legacy default namespace also searches `/vendor/${LIB}/hw` (FM, ANT and `libbt-hidlclient` load
    `bluetooth@1.0-impl-qti` by name);
  - new **`legacy_vendor`** section with `/system/${LIB}/atu-compat` first — gives the RIL daemon, the
    Widevine HAL and the audio HAL the Android 9 protobuf they were built against (see VENDOR-AUDIT C);
  - `bionic/linker/linker_config.cpp`: a `dir.` entry may be a full binary path, so a section can be
    assigned to a single executable.
- **Verified:** `/linkerconfig/ld.config.txt` contains the section; `rild`, `drm-widevine-hal` load protobuf v28.

### 1.7 Missing / changed symbols
| Missing in Android 12 | Used by | Fix |
|---|---|---|
| `android::base::LogMessage(file,line,LogId,LogSeverity,int)` | BT impl, Wi-Fi HAL, Huawei libs | old constructor added to `system/libbase` |
| `tinyxml2::XMLDocument(bool)` | Huawei iawareperf | constructor added to `external/tinyxml2` |
| HIDL `toString()`s, `IHealth::descriptor`, `IPCThreadState::disableBackgroundScheduling` | sensors, health, wpa_supplicant | `libatu_shim` (device/compat); `libhidltransport` now links it (`system/libhidl`) |
| `android_log_shouldPrintLine`, `android_log_printLogLine` | Huawei `libhwlog` | exported in `liblog.map.txt` |
| `android.hidl.base@1.0.so`, `android.hidl.manager@1.0.so` | almost every 8.0 HAL | stub libraries (device/compat) |
| ICU 58 `ucnv_*` | Huawei libs | `libicuuc` stub |
| `libwifi-system` → `InterfaceTool` | Wi-Fi HAL | depends on `libwifi-system-iface` (`frameworks/opt/net/wifi`) |

### 1.8 vndservicemanager, health, render engine, GNSS
- The 8.0 `vndservicemanager` links `libhwlog` and speaks the old protocol → Android 12 build of it is used
  (`frameworks/native/cmds/servicemanager`: `atu_vndservicemanager`, declared under the same service name).
- SkiaGL render engine fails on the 8.0 Adreno driver (`Unable to generate SkImage`) →
  `debug.renderengine.backend=gles`.
- GNSS: framework manifest fragment for `IGnss`/`gnss_vendor` (ILocHidlGnss parent check).

**Result:** `sys.boot_completed=1`, home screen, touch, Wi-Fi.

---

## 2. The Parcel ABI fix (RIL, camera, display)

- **Symptoms:** `per_proxy` crashes → modem never comes ONLINE → `com.android.phone` ANRs; after any camera
  provider restart `openCamera` loops on *stack corruption*; display utilities (`mm-pp-dpps`) crash.
- **Cause:** 8.0 vendor code allocates `android::Parcel` **on its own stack** with the 8.0 size —
  104 bytes (64-bit) / 52 bytes (32-bit). The Android 12 `Parcel` is 120 / 60 bytes, so the Android 12
  constructor writes 16 / 8 bytes past the object into the caller's frame. Measured by disassembling
  `libperipheral_client` (Parcels at `sp+0x18`/`sp+0x80`, 104 bytes apart).
- **Rejected alternative:** giving vendor processes the Android 9 `libbinder` fixes the layout but mixes binder
  protocols on `vndbinder` (Android 12 servicemanager ↔ old clients).
- **Fix:** `frameworks/native/libs/binder/include/binder/Parcel.h` + `Parcel.cpp`: the six bool flags and the
  work-source position are packed into **one 32-bit bit-field word** (26-bit position + 6 flags). The first
  nine fields keep their 8.0 offsets; the size is again 104 / 52 bytes, guarded by `static_assert`.
  Only the in-memory layout changes — the wire format is identical, so no app or HAL notices.
- **Verified:** modem ONLINE, `gsm.version.baseband` set, Qualcomm RIL 1.0 with both SIM slots,
  no `per_proxy`/camera/`mm-pp-dpps` crashes after hours of use.
- How it was found: [VENDOR-AUDIT.md](VENDOR-AUDIT.md).

---

## 3. Smooth UI

### 3.1 Too many layers for the 8.0 HWC
- **Symptom:** home screen scrolling 10–14 FPS.
- **Measurement:** `dumpsys SurfaceFlinger --latency <layer>` (gfxinfo is useless here: HWUI GPU timestamps are
  `INT64_MAX`). SurfaceFlinger logs `All strategy failed, falling back to GPU`.
- **Cause:** the 8.0 SDM HWC cannot handle 6 layers (zoomed wallpaper + two `ScreenDecorOverlay` layers for the
  privacy dot), so every frame is GPU-composed — which is slow, see 3.2.
- **Fix (RROs in device/atu):** `config_enablePrivacyDot=false`; `config_wallpaperMaxScale=1.0`;
  rounded corners 0. Also `persist.sys.sf.color_saturation=1.0` — the default "boosted" 1.1 forces GPU
  composition too.
- **Verified:** 57 FPS home, 56 FPS Settings.

### 3.2 Adreno 308 GPU composition costs 75 ms per frame
- **Cause (stack sampling with `debuggerd -b` on SurfaceFlinger):** `rb_perform_binning_resolve/unresolve` in
  the 8.0 driver — tiled (binning) rendering of full-screen layers.
- **Fix:** `frameworks/native/libs/renderengine/gl/GLESRenderEngine.cpp`: after context creation,
  `glHint(GL_BINNING_CONTROL_HINT_QCOM, GL_RENDER_DIRECT_TO_FRAMEBUFFER_QCOM)`, mode via
  `debug.atu.re_binning` (0–3, default 3 = direct).
- **Verified:** `drawLayers` 77 ms → 2.4 ms; recents ~46 FPS (was ~12); warm app start ~120 ms.

### 3.3 Low RAM tuning (2 GB)
`ro.config.low_ram=true`; dalvik heap 8m/128m/256m (vendor `default.prop` sets `heapsize=36m`!); lmkd without PSI
(3.18 has none): `ro.lmk.use_psi=false`, `use_minfree_levels=true`; `dex2oat` 2 threads.

---

## 4. Media

### 4.1 Browsers hang: endless wait for the OMX service
- **Symptom:** Firefox loads no page at all (internal requests time out); WebView apps freeze.
- **Cause:** Gecko's main thread waits in `MediaCodecList` → `mediaserver.getCodecList` → HIDL `getService` for
  `IOmx`/`IOmxStore`, which is declared in the vendor manifest but whose 8.0 binary cannot start → waits forever.
- **Fix (`frameworks/av`):** `tryGetService` instead of `getService` in `OmxInfoBuilder`, `OMXClient`, `CCodec`,
  `MediaPlayerService`, `MediaRecorderClient`.
- **Verified:** pages load; codec list query 45 ms (`tools/tests/CodecTest`).

### 4.2 Empty codec lists
- **Cause:** the 8.0 `media_codecs_performance.xml` references `OMX.qti.video.decoder.mpeg4sw`, which does not
  exist → `BAD_VALUE` → the builders threw away **all** codecs (0 Codec2, 0 OMX).
- **Fix:** `Codec2InfoBuilder.cpp`, `OmxInfoBuilder.cpp`: log a warning and continue.
- **Verified:** 53 Codec2 codecs, later 62 with OMX.

### 4.3 No sound at all
- **Symptom:** every output fails with `cannot set hw params`; dmesg `tfa98xx: invalid sample rate 48000`.
- **Cause:** the TFA9872 amplifier driver requests `tfa98xx.cnt` through ueventd (firmware user helper). The file is
  in `/odm/etc/firmware`, which Android 12 ueventd does not search → empty rate table.
- **Fix:** `system/core/rootdir/ueventd.rc`: `firmware_directories /odm/etc/firmware/`. No Huawei file is shipped.
- **Verified:** `Firmware init complete`, `tools/tests/ToneTest` 96000/96000 frames, audible.

### 4.4 Software video: "gralloc-mapper is missing"
- **Symptom:** video does not play; `mediaswcodec` aborts when decoding to a Surface.
- **Cause:** `linkerconfig` decides "VNDK available" only by the presence of a `com.android.vndk.*` APEX (the GSI
  has `current`), so the APEX `sphal` namespace has no `/system/${LIB}` and the vendor gralloc mapper cannot
  load `android.hardware.graphics.mapper@2.0.so`.
- **Fix:** `system/linkerconfig/contents/namespace/sphal.cc`: also add `/system/${LIB}` when `IsLegacyDevice()`.
- **Verified:** `tools/tests/SurfTest` decodes 60 frames in 296 ms (`c2.android.avc.decoder`).
- Note: seccomp was suspected first and ruled out (same abort with a permissive policy).

### 4.5 Hardware video decoding (Qualcomm OMX)
- **Cause:** the 8.0 vendor OMX service links `libmediacodecservice.so` and other 8.0 **system** libraries.
- **Fix:** `frameworks/av/services/mediacodec/Android.bp`: `atu_omx_service` — the same service built for the
  system partition (32-bit, no software OMX) at `/system/bin/hw/android.hardware.media.omx@1.0-service`; the
  `mediacodec` service is redirected to it in `atu-overrides.rc`. It loads `/vendor/lib/libstagefrighthw.so`.
- **Verified:** `OMX.qcom.video.decoder.avc` 60 frames in 204 ms; H.264, HEVC and VP8 in hardware; YouTube in
  Firefox plays via OMX (`media.resource_manager`). VP9/AV1 have no hardware support on MSM8917.

### 4.6 Perflock aborts (video and camera)
- **Cause:** the video decoder and camera `dlopen` `ro.vendor.extension_library` (`libqti-perfd-client`), whose
  8.0 perf HAL aborts in `perf_lock_rel` with a HIDL error.
- **Fix:** `ro.vendor.extension_library=none`.
- **Verified:** no crash loop; both cameras available.

### 4.7 Widevine
- Runs in the `legacy_vendor` section (Android 9 protobuf). Only `drm@1.0-service.widevine` — putting the
  clearkey `drm@1.0-service` there broke it, because Android 12 `libmediadrm` needs the new protobuf.
- **Verified:** `isCryptoSchemeSupported` = true (`tools/tests/DrmTest`). Expect L3.

---

## 5. Apps and services

| Change | Why |
|---|---|
| `frameworks/base` `PackageManagerService.java` | phh signature spoofing replaced only `signatures`; `GET_SIGNING_CERTIFICATES` → `signingInfo` still returned the real microG signature and the microG self-check failed. `signingInfo` now gets the spoofed signature too. Verified with `tools/tests/SigTest`. |
| `frameworks/base` `Build.java` *(v11, not yet tested)* | "There's an internal problem with your device" at every boot: `Build.isBuildConsistent()` → VINTF check fails with *No kernel entry found for kernel version 3.18*. The result is now only logged. |
| `external/chromium-webview` | WebView 95 → LineageOS Chromium WebView **154.0.8037.57**; `optional_uses_libs` to pass `manifest_check`. |
| `packages/apps/Jelly` | LineageOS browser (lineage-19.1), `overrides: ["Browser2"]`. |
| `device/phh/treble` | `ro.logd.auditd=false` (permissive mode floods logd); Bluetooth default name "HUAWEI ATU-L21". |
| SettingsProvider RRO | clean-install defaults: charging sound/vibration off. |
| Product props | `ro.product.brand=HUAWEI` (vendor says "Android"), system model/manufacturer. |

### microG flavour (`vendor/atu/atu-microg`)
GmsCore, Companion, GsfProxy and Aurora Store as privileged system apps with the original signatures.
The build system would store JNI libs uncompressed and break the v2 signature of a presigned APK, so the APKs
are installed unchanged (`LOCAL_REPLACE_PREBUILT_APK_INSTALLED`) and GmsCore's arm64 libraries are pre-extracted.
Permissions/sysconfig XMLs grant `FAKE_PACKAGE_SIGNATURE` and location provider roles.

### Vanilla flavour (`vendor/atu/atu-apps`)
F-Droid is installed at first boot (`atu-firstboot-apps`, shell domain, `pm install` after `boot_completed`,
done flag `settings global atu_apps_done=1`) — a system app would not be updatable in place without wasting space.

---

## 6. Things that were tried and dropped
- Android 9 `libbinder` for vendor processes (see 2) — protocol mix-up on vndbinder.
- libselinux "last definition wins" for duplicate contexts — the `hwservice_contexts` edit is smaller.
- Running `linkerconfig` manually after boot — phh's `vndk.rc` sets `ro.vndk.version=26` later, a manual run
  generates a VNDK-mode config and breaks the system.
- Firefox Focus as a system app — APK + extracted libs do not fit in the system partition.
