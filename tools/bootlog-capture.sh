#!/bin/bash
# Wait until the device shows up on adb in Android mode (not recovery), then keep saving
# logcat, dmesg and getprop for up to 10 minutes. Useful for catching early-boot failures.
# Usage: bootlog-capture.sh <prefix>   -> logs/<prefix>-*.txt (in the current directory)
set -u
mkdir -p logs
P=logs/${1:?usage: bootlog-capture.sh <prefix>}
echo "$(date +%T) waiting for adb" > "$P-status.txt"
until [ "$(adb get-state 2>/dev/null)" = "device" ]; do sleep 1; done
echo "$(date +%T) adb up" >> "$P-status.txt"
adb shell getprop > "$P-getprop-first.txt" 2>&1
adb logcat -b all -v threadtime > "$P-logcat.txt" 2>&1 &
LC=$!
for _ in $(seq 1 120); do
  adb shell dmesg > "$P-dmesg.txt" 2>&1 || adb shell su -c dmesg > "$P-dmesg.txt" 2>&1
  adb shell getprop > "$P-getprop.txt" 2>&1
  [ "$(adb get-state 2>/dev/null)" = "device" ] || { echo "$(date +%T) adb lost" >> "$P-status.txt"; break; }
  sleep 5
done
kill $LC 2>/dev/null
echo "$(date +%T) done" >> "$P-status.txt"
