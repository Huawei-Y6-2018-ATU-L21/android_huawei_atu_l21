# How the port progressed

## Before: ready-made GSIs (none booted)
More than ten A-only GSIs (AOSP 8–11, crDroid, LineageOS) had been tried — stuck at the Huawei logo, at the
boot animation, or no boot at all. No logs were taken. Lesson: without logs every attempt is a coin toss.

## Attempt 1 — phh v123 (Android 9, A-only): boots
Flash `system`, format data in TWRP, boot. Display, touch, sound, Wi-Fi, Bluetooth, sensors and both cameras
worked; fingerprint HAL missing. Conclusion: the device is fine — earlier failures were procedure and Android version.

## Attempt 2 — phh v222 (Android 10, A-only): crash loop
`vold: Unable to find device keyring` → FBE keys not installed → `system_server` loop → recovery.
Root cause: the ramdisk still runs the **8.0 init**, which does not create the keyring Android 10 expects.

## Attempt 3 — Android 10 + ramdisk without FBE: boots
A bind-mounted fstab without `fileencryption` (added to the stock ramdisk with `tools/ramdisk_add.py`) confirmed
the diagnosis. Android 10 booted unencrypted. Next step: a modern init instead of workarounds.

## Attempts 4–6 — Android 12 (v416) with an Android 12 first-stage ramdisk
- 4: reboot to fastboot during the unlock warning, no log. Found: the bootloader ignores the ramdisk header cmdline.
- 5: debug init (kmsg dump + recovery target): first stage, `switch_root`, SELinux and `/data` all passed; failure is
  in the second stage.
- 6: with a 180 s wait the dump worked: `hwservicemanager` aborted — duplicate tetheroffload contexts.

## Booting Android 12 (own kernel 3.18.140)
Fixed in order: odm dm-verity loop (DTB), verity/FBE markers, init watcher hang, ueventd legacy paths, root mount
points, `ro.build.*` override, linkerconfig aborts, compat libraries, liblog exports, Android 12 vndservicemanager,
stdio→kmsg, GLES render engine, mount_all, health 2.0, adb FunctionFS, cgroup v1, audio HidlUtils, subcontext,
wifi-system, GNSS manifest. Then Huawei BFM (eRecovery after 10 min) and a stuck `misc` command.
→ `sys.boot_completed=1`.

## Making it usable
| Version | Main change |
|---|---|
| v416-dbg | modified phh image, Go tuning; UI fixed (overlays 10 → 57 FPS, Adreno binning hint 77 → 2.4 ms) |
| v1 | first clean build from source: `atu_l21-userdebug` product, no phh-su |
| v2 | two flavours (vanilla / microG), brand/model, clean-install defaults |
| v3 | microG signature spoofing also for `signingInfo` |
| v4 | browsers work: OMX `tryGetService`, Codec2 XML tolerance, linkerconfig sphal (video) |
| v5 | sound: amplifier firmware path |
| v6 | hardware video decoding (system-side OMX service), perflock off |
| v7 | vendor audit fixes: **Parcel ABI** → RIL/modem, camera stable; protobuf compat; Bluetooth |
| v8 | Widevine linker fix, Bluetooth name and default |
| v9 | preinstalled apps (not released) |
| v10 | Jelly + WebView 154, F-Droid at first boot (vanilla) — **first public release** |

## Next
v11 (VINTF dialog fix), SIM tests, Magisk, newer TWRP, SELinux enforcing; a LineageOS 19.1 base is being considered.
