#!/bin/bash
# Build one of the on-device test programs and run it with app_process (needs adb; root for some).
# Requires: javac, an Android SDK android.jar (API 31) and D8 (r8.jar).
# Usage: ANDROID_JAR=.../android.jar R8_JAR=.../r8.jar ./run.sh CodecTest [args...]
#   CodecTest              list all codecs and how long MediaCodecList takes
#   DecTest                create + start c2 software decoders (avc, vp9, aac)
#   SurfTest <mp4> [codec] decode an mp4 into a Surface (default c2.android.avc.decoder;
#                          use OMX.qcom.video.decoder.avc for the hardware decoder)
#   ToneTest               play a 2 s test tone
#   SigTest <pkg...>       print signature SHA-1 via GET_SIGNATURES and GET_SIGNING_CERTIFICATES
#   DrmTest                check Widevine support (MediaDrm needs an app context; partial)
set -e
CLS=${1:?test class}; shift
OUT=$(mktemp -d)
javac --release 8 -cp "${ANDROID_JAR:?}" -d "$OUT" "$(dirname "$0")/$CLS.java"
java -cp "${R8_JAR:?}" com.android.tools.r8.D8 --output "$OUT" --lib "$ANDROID_JAR" "$OUT"/*.class
adb push "$OUT/classes.dex" /data/local/tmp/atutest.dex >/dev/null
for a in "$@"; do case "$a" in *.mp4) adb push "$a" /data/local/tmp/ >/dev/null;; esac; done
args=(); for a in "$@"; do case "$a" in *.mp4) args+=("/data/local/tmp/$(basename "$a")");; *) args+=("$a");; esac; done
adb shell CLASSPATH=/data/local/tmp/atutest.dex app_process /system/bin "$CLS" "${args[@]}"
