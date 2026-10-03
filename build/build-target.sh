#!/bin/bash
# Run inside the build container. Usage: LUNCH=atu_l21-userdebug build-target.sh systemimage
cd /src
export USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache CCACHE_DIR=/ccache
export ALLOW_MISSING_DEPENDENCIES=true SKIP_ABI_CHECKS=true
source build/envsetup.sh >/dev/null
lunch "${LUNCH:-atu_l21-userdebug}" >/dev/null || exit 1
m -j"${JOBS:-8}" "$@" && echo BUILD_OK || echo BUILD_FAIL
