# Known issues (v10)

## Not yet tested
- **Calls, SMS, mobile data with a SIM.** The modem is ONLINE and RIL reports the baseband and both SIM slots,
  but no SIM has been tested yet. Reports are very welcome.
- GPS fix outdoors, fingerprint enrolment, MTP, FM radio, VoLTE.
- Widevine with a real streaming app (expected level: L3).

## Open
| Issue | Details / workaround |
|---|---|
| SELinux **permissive** | the 8.0 vendor policy does not cover the Android 12 system services; enforcing needs a policy merge |
| "There's an internal problem with your device" dialog at boot | harmless; the VINTF kernel check fails for 3.18. Fixed in source (`Build.java`), will be in v11 |
| No setup wizard; time zone defaults to GMT | set the time zone in Settings → System → Date & time |
| Boot animation | may not show: `BootAnimation::readyToRun` crashed in early builds (cosmetic) |
| Debug init still active | on a fatal init error the phone waits 180 s and goes to recovery; harmless on a working system |
| Camera portrait mode | needs proprietary `libtrueportrait`, not shipped |
| VP9 / AV1 video | software decoding only (no hardware support on MSM8917) — slow above 480p. Prefer H.264 (e.g. the *enhanced-h264ify* add-on or NewPipe) |
| YouTube in Firefox | the quality menu does not open in **fullscreen** (website layout); works in portrait |
| Official YouTube app with microG | asks for a newer microG; use NewPipe or ReVanced |
| Some Flutter apps crash | crash inside the 8.0 Adreno shader compiler (`libsc-a3xx.so`), a driver bug |
| No root | Magisk support is planned; phh-su is not included |
| TWRP 3.2.3 | cannot format data on Android 12 (use `mkfs.f2fs`, see FLASHING) and cannot read Android 12 settings; a newer TWRP is planned |

## Performance notes
- 2 GB RAM: the build is tuned as Android Go (`ro.config.low_ram=true`). Heavy apps and many tabs will be killed
  in the background.
- If animations stutter after you change display settings (colour mode, saturation), set them back: anything
  other than 1.0 saturation forces GPU composition (see PATCHES §3).
