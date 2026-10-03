#!/bin/bash
# Download the phh v416 (android-12.1.0_r11) tree with the slim manifest and pin every project
# to the exact commit the release was built from.
# Usage: sync.sh <tree dir> <path to atu_l21_patches>
set -eu
TREE=${1:?usage: sync.sh <tree> <atu_l21_patches>}; P=$(realpath "${2:?}")
mkdir -p "$TREE"; cd "$TREE"
repo init -u https://github.com/phhusson/treble_manifest -b android-12.0
cp "$P/manifest/phh-v416-slim.xml" .repo/manifests/
repo init -m phh-v416-slim.xml
# Google's servers sometimes answer RESOURCE_EXHAUSTED; wait and retry.
for try in $(seq 1 12); do
  echo "sync attempt $try $(date +%T)"
  repo sync -c -j4 --no-tags --no-clone-bundle --optimized-fetch --retry-fetches=3 && break
  [ "$try" = 12 ] && { echo "sync failed"; exit 1; }
  sleep 300
done
while read -r path sha; do
  [ -d "$path" ] && git -C "$path" checkout -q "$sha"
done < "$P/manifest/pinned-revisions.txt"
echo "sync done"
