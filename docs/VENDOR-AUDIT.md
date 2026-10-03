# Vendor audit: 8.0 vendor against Android 12

After the first fixes the ROM booted, but individual services kept failing one by one. Instead of chasing them,
every ELF file on `vendor` and `odm` was checked statically against the Android 12 system.

```bash
# ROOT/vendor, ROOT/odm      — pulled from the phone
# ROOT/sys/lib, sys/lib64, sys/apex/<name>/lib{,64} — from the Android 12 system image
python3 tools/vendor_audit.py ROOT --md audit.md --json audit.json
```

Checks per ELF:

1. **NEEDED resolution** with the search order vendor processes really get (legacy linkerconfig:
   `/system → /vendor → /odm`, bionic from the runtime APEX).
2. **Unresolved global symbols** against the full dependency closure.
3. **ABI risk:** code that constructs system classes whose size or layout changed since 8.0
   (constructor calls on stack/heap memory the caller sized itself).

Result: **4816 ELFs** (3963 32-bit, 853 64-bit), **65 with findings** — 29 missing libraries,
42 unresolved symbols, 15 ABI risks.

## A. `android::Parcel` size — critical

`sizeof(Parcel)` was 104 / 52 bytes in 8.0 and is 120 / 60 in Android 12. Measured in
`libperipheral_client`: two stack Parcels at `sp+0x18` and `sp+0x80` (104 bytes apart; 32-bit: `sp+0x04`/`sp+0x38`).

Affected: `libperipheral_client` (modem start, GPS, subsystem control), `camera.msm8937.so`, `libqdutils`,
`libqservice`, `libsdm-disp-vndapis` (display), `libthpinterface` (Huawei touch), `libwfdmmservice` (wireless
display), `vndservice`, `hw_diag_server`.

Decision: pack the Parcel flags so the size matches 8.0 → [PATCHES.md §2](PATCHES.md#2-the-parcel-abi-fix-ril-camera-display).
This single change fixed RIL/modem, the camera restart loop and the display post-processing daemon.

## B. Libraries that were in the 8.0 `/system` and are gone

| Library | Used for | Decision |
|---|---|---|
| `libwebrtc_audio_preprocessing` | call noise suppression / echo cancellation effect | shipped from stock (AOSP code, BSD) in `atu-compat` |
| `libmediacodecservice` | 8.0 OMX service | not needed: system-side OMX service |
| `libtrueportrait` | camera portrait mode | proprietary, not redistributed — portrait mode missing |
| `libmm-qdcm-diag`, `libmm-dspp-utils`, `libllvd_smore`, `liboemcrypto`, `libloc_externalDrcore`, `libgcc` | — | also missing on stock: optional `dlopen`s, ignore |

## C. Old protobuf API

`libsettings` (RIL), `libwvhidl`/`libwvdrmengine` (Widevine) and the audio preprocessing library need the
protobuf of their era (`empty_string_`, `Arena::AddListNode`, …). Android 9 (VNDK 28) protobuf is placed in
`/system/${LIB}/atu-compat` and only given to those processes through the `legacy_vendor` linkerconfig section,
so nothing else sees two protobuf versions.

## D. Old symbols

| Symbol | Users | Fix |
|---|---|---|
| `LogMessage(..., LogSeverity, int)` (8×) | BT, Wi-Fi HAL, Huawei libs | old constructor in `libbase` |
| `tinyxml2::XMLDocument(bool)` | Huawei iawareperf | constructor in `tinyxml2` |
| sensors `V1_0::toString(Result)` | `slim_daemon` | `libatu_shim` |

These were first in `libatu_shim`, but that only reaches processes loading the hidl.base stub; moving them into
the real libraries covers all users.

## E. `/vendor/lib*/hw` search path

FM, ANT and `libbt-hidlclient` load `android.hardware.bluetooth@1.0-impl-qti.so` by name, which lives in
`hw/`. Added to the legacy default namespace.

## F. Ignored

`health@1.0` (replaced by 2.0), old OMX (replaced), `libhwbinder` test implementations, ADSP/rfsa (DSP side),
`lib-sec-disp` (secure display, old API), keymaster provisioning tools (`KmInstallKeybox`, `attest_provision`).

## Runtime check

After the fixes every vendor service was watched for restarts (`init: Service ... exited`), linker errors and
aborts over several boots and hours of use. Remaining issues: [KNOWN-ISSUES.md](KNOWN-ISSUES.md).
