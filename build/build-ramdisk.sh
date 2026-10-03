#!/bin/bash
# Run inside the build container. Builds the Android 12 first-stage init ramdisk with phh's generic target.
# Output: out/target/product/phhgsi_arm64_ab/ramdisk.img (lz4 cpio)
cd /src
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache CCACHE_DIR=/ccache ALLOW_MISSING_DEPENDENCIES=true
(cd device/phh/treble && bash generate.sh) || exit 1
source build/envsetup.sh
lunch treble_arm64_bvS-userdebug || exit 1
m -j"${JOBS:-8}" init_first_stage ramdisk && echo BUILD_OK || echo BUILD_FAIL
