# Debugging techniques

Porting to an old vendor is mostly about **seeing** why something fails. These are the methods that found
every problem in [PATCHES.md](PATCHES.md).

## 1. The phone does not boot — where are the logs?

The stock kernel has no pstore and Huawei's `log` partition only holds stock recovery logs, so the first
Android 10/12 attempts failed silently. Three things fixed that:

1. **Debug init** (`system/core/init/reboot_utils.cpp` patch): on a fatal init error the kernel log goes to
   `/cache/init-fatal/kmsg-<boot_id>.txt`, then init waits 180 s before rebooting to recovery
   (`androidboot.init_fatal_reboot_target=recovery` in the kernel cmdline). Read it from TWRP.
2. **pstore/ramoops** in the kernel (4 MiB at 0x8f100000, console + pmsg). After *any* reboot, in TWRP:
   ```bash
   mkdir -p boot1/pstore && adb pull /sys/fs/pstore boot1/
   python3 tools/pull_pstore.py boot1          # -> console.txt, logcat-pmsg.txt
   python3 tools/summarize_boot.py boot1       # crashing services, linker errors, abort messages
   ```
   `pmsg` contains logcat (Android writes it there), so you get logcat of a boot that never reached adb.
3. **Live capture:** `tools/bootlog-capture.sh <name>` waits until adb comes up in Android and keeps saving
   logcat, dmesg and getprop for 10 minutes. Start it before rebooting.

`adb` works from early boot: the build is `userdebug` with `ro.adb.secure=0`.

## 2. Crashes and hangs

- **Tombstones** (`/data/tombstones`) — but stack corruption in 8.0 code often produces none.
- **Stack sampling:** `adb shell debuggerd -b <pid>` dumps all thread stacks without killing the process.
  Repeating it a few times shows where CPU time goes — this found the Adreno binning resolve (75 ms per frame)
  and the infinite `getService` wait in mediaserver.
- **`dumpsys SurfaceFlinger --latency <layer>`** for real frame times. `dumpsys gfxinfo` is not usable here:
  HWUI's GPU-completed timestamps are `INT64_MAX` with this driver.
- `logcat -b all`, filter `CANNOT LINK`, `cannot locate symbol`, `Abort message`, `avc: denied`
  (SELinux is permissive, so denials are logged but not enforced — they still hint at mislabeled files).

## 3. Testing without a reflash

The system image has no shared blocks, so after `adb root`:

```bash
adb shell mount -o rw,remount /
adb push out/.../libfoo.so /system/lib64/libfoo.so   # keep a backup of the original!
adb shell restorecon /system/lib64/libfoo.so
adb shell stop; adb shell start                      # or restart only the affected service
```

For an image on the PC, `tools/img_put.py` puts a file into the raw image with mode, owner and SELinux label
(via `debugfs`) and verifies the result.

## 4. Small on-device test programs (`tools/tests`)

Plain Java classes run with `app_process` — no APK, no install, run in seconds:

| Test | Checks |
|---|---|
| `CodecTest` | codec list and how long `MediaCodecList` takes (found the OMX wait and the empty list) |
| `DecTest` | software decoders can be created and started |
| `SurfTest <mp4> [codec]` | decode into a Surface — the path video apps use (found the gralloc mapper problem); with `OMX.qcom.video.decoder.avc` it tests hardware decoding |
| `ToneTest` | plays a 2 s tone and reports frames written (found the amplifier firmware problem) |
| `SigTest <pkg>` | signature via both `GET_SIGNATURES` and `GET_SIGNING_CERTIFICATES` (microG spoofing) |
| `DrmTest` | Widevine scheme support |

```bash
ANDROID_JAR=~/Android/Sdk/platforms/android-31/android.jar R8_JAR=~/r8.jar tools/tests/run.sh CodecTest
```

## 5. Vendor compatibility

Static checks of all vendor/odm ELFs against the Android 12 system (`tools/vendor_audit.py`,
`tools/vendor_symcheck.py`) — see [VENDOR-AUDIT.md](VENDOR-AUDIT.md).

## 6. Images and firmware

| Tool | Purpose |
|---|---|
| `huawei_app.py` | list/extract `UPDATE.APP` |
| `kernel_pack.py` | build a Huawei kernel-only boot image (cmdline lives here) |
| `ramdisk_replace.py` / `ramdisk_add.py` | replace the whole ramdisk cpio / add files to the stock one |
| `dtb_list.py` | list the appended DTBs (model, msm-id, board-id) |

## Tips learned the hard way

- Never run `linkerconfig` by hand on a running system (see HOW-IT-WORKS).
- A clean userdata reveals defaults you never noticed on a long-used test install — test both.
- Disproving a hypothesis is progress: write it down (seccomp was not the reason `mediaswcodec` aborted).
- Huawei eRecovery can leave a command in `misc`; if every boot ends in TWRP, check it first.
