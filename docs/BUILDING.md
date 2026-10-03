# Building from source

You need three things: the **system image** (the ROM), the **ramdisk** (Android 12 first-stage init) and
the **kernel**. The released ramdisk and kernel rarely change, so most people only rebuild the system image.

## Requirements

| | |
|---|---|
| Disk | ~250 GB for the tree + out, 50 GB for ccache |
| RAM | 32 GB recommended; with 16 GB add swap and use `JOBS=4` |
| Host | any Linux with Docker; the build runs in Ubuntu 20.04 (`build/docker/Dockerfile`) |
| Stock firmware | the ATU-L21 `UPDATE.APP` (any 8.0 C432 build) — only for the ramdisk/kernel headers |

```bash
docker build -t atu-l21-builder --build-arg UID=$(id -u) --build-arg GID=$(id -g) build/docker
```

## 1. Source tree

The base is phh-treble **v416** (`android-12.1.0_r11`). The slim manifest drops `vendor/partner_gms` (its
branch no longer exists) and ~46 unrelated `device/*` projects. `pinned-revisions.txt` pins all 1017 projects to
the commits the release was built from — without it you get today's heads, and the patches may not apply.

```bash
git clone https://github.com/Huawei-Y6-2018-ATU-L21/atu_l21_patches
git clone https://github.com/Huawei-Y6-2018-ATU-L21/android_huawei_atu_l21
android_huawei_atu_l21/build/sync.sh ~/a12 atu_l21_patches          # repo init + sync + pin
```

## 2. Patches, device and vendor

```bash
atu_l21_patches/apply.sh ~/a12             # patches 16 projects, clones Jelly, downloads WebView 154
git clone https://github.com/Huawei-Y6-2018-ATU-L21/android_device_huawei_atu_l21 ~/a12/device/atu
git clone https://github.com/Huawei-Y6-2018-ATU-L21/android_vendor_atu ~/a12/vendor/atu
~/a12/vendor/atu/fetch-prebuilts.sh        # microG, Aurora, F-Droid APKs (SHA256-verified)
cp android_huawei_atu_l21/build/build-*.sh ~/a12/
```

The phh product makefiles are generated, as for any phh build:

```bash
(cd ~/a12/device/phh/treble && bash generate.sh)
```

## 3. System image

```bash
run() {  # run a command in the build container
  docker run --rm -e LUNCH -e JOBS -v ~/a12:/src -v ~/ccache:/ccache atu-l21-builder bash -c "$*"
}
mkdir -p ~/ccache && run ccache -M 50G

LUNCH=atu_l21-userdebug        run /src/build-target.sh systemimage   # vanilla
LUNCH=atu_l21_microg-userdebug run /src/build-target.sh systemimage   # microG
```

Both products share `PRODUCT_DEVICE`, so they use the same out directory: build one, copy
`out/target/product/atu_l21/system.img`, then build the other. The image is a **raw** ext4 image of exactly
0xa4000000 bytes (no sparse format, no shared blocks — TWRP can mount it read-write).

A first build takes 4–6 hours on 8 cores; incremental builds with ccache 10–30 min.

> Run the build in the foreground (or in `tmux`). Detached `docker run ... &` builds were observed to die
> silently during Soong glob regeneration.

Check the result:

```bash
grep -E 'ro.build.flavor|ro.product.system.model' ~/a12/out/target/product/atu_l21/system/build.prop
```

## 4. Ramdisk

The ramdisk only needs Android 12 `init` (first stage) and the root skeleton; it is built with phh's
generic target and re-packed with the **stock** ramdisk header (load addresses, page size):

```bash
run /src/build-ramdisk.sh
python3 tools/huawei_app.py extract UPDATE.APP stock/ RAMDISK KERNEL     # -> stock/ramdisk.img, stock/kernel.img
lz4 -dc ~/a12/out/target/product/phhgsi_arm64_ab/ramdisk.img > ramdisk-a12.cpio
python3 tools/ramdisk_replace.py stock/ramdisk.img ramdisk-a12.cpio ramdisk-a12-2si.img \
    --append-cmdline "androidboot.boot_devices=soc/7824900.sdhci"
```

`ramdisk_replace.py` compresses with gzip — the stock kernel config has `CONFIG_RD_GZIP` but no LZ4. The header
cmdline of the ramdisk image is ignored by the bootloader; the appended value is only informational.

## 5. Kernel

```bash
git clone -b atu-l21-a12 https://github.com/Huawei-Y6-2018-ATU-L21/android_kernel_huawei_atu_l21 kernel
git clone https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9 gcc49
git -C gcc49 checkout 961622e
cd kernel && CROSS=$PWD/../gcc49/bin/aarch64-linux-android- ./build_atu_l21.sh out && cd ..

python3 tools/kernel_pack.py stock/kernel.img kernel/out/arch/arm64/boot/Image.gz-dtb kernel-atu.img --cmdline \
 "androidboot.hardware=qcom msm_rtb.filter=0x237 ehci-hcd.park=3 lpm_levels.sleep_disabled=1 androidboot.bootdevice=7824900.sdhci slub_min_objects=12 unmovable_isolate1=2:192M,3:224M,4:256M unmovable_isolate2=2:64M,3:80M,4:80M androidboot.selinux=permissive ramoops.mem_address=0x8f100000 ramoops.mem_size=0x400000 ramoops.console_size=0x200000 ramoops.pmsg_size=0x100000 ramoops.record_size=0x40000 androidboot.init_fatal_reboot_target=recovery"
```

The kernel must be built with GCC 4.9 (the 3.18 tree does not build with clang/new GCC). The build script
enables SELinux develop mode (permissive) and pstore/ramoops, and disables WireGuard and FORTIFY_SOURCE.
The cmdline lives in the **kernel** image header — that is where the bootloader takes it from.

## 6. Compress for release

```bash
xz -T0 -9 -k system.img        # GitHub release assets are limited to 2 GB
sha256sum *.img *.xz > SHA256SUMS
```

## Adding your own change

1. Edit the project in `~/a12`, mark it with an `// ATU-L21:` comment.
2. Rebuild the module only and push it to a running device for testing; the system partition can be remounted
   read-write (`adb root && adb shell mount -o rw,remount /`). Keep a copy of the original file.
3. Rebuild `systemimage`, flash, verify on a **clean** userdata as well.
4. `git -C ~/a12/<project> diff > atu_l21_patches/patches/<project>.patch` and document the change in
   [PATCHES.md](PATCHES.md) with symptom, cause, fix and how you verified it.

## Common build errors

| Error | Fix |
|---|---|
| `RESOURCE_EXHAUSTED` during sync | Google rate limit; `sync.sh` waits 5 min and retries |
| `manifest_check` for `webview` | `external_chromium-webview.patch` not applied (`optional_uses_libs`) |
| VINTF fragment in `PRODUCT_COPY_FILES` rejected | fragments are attached to `libatu_shim` with `vintf_fragments` |
| Service starts on old builds but not here: `init: ... has no SELinux domain` | add the binary to `device/atu/atu_l21/sepolicy/file_contexts` |
| Product variables lost (`BOARD_*` dynamic partitions) | common makefile must be `include`d, not `inherit-product` |
| ABI dump mismatch after the Parcel / liblog change | `SKIP_ABI_CHECKS=true` (set by `build-target.sh`) |
