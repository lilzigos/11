#!/usr/bin/env bash
set -euo pipefail
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
mkdir -p runtime-evidence
emulator -avd sgm-r11 -accel on -gpu swiftshader_indirect -no-window -no-audio -no-boot-anim -no-snapshot -cores 2 -memory 4096 -skin 1280x720 -feature -Vulkan > runtime-evidence/emulator.log 2>&1 &
emulator_pid=$!
trap 'kill "$emulator_pid" 2>/dev/null || true' EXIT
timeout 180 adb wait-for-device
booted=false
for attempt in $(seq 1 90); do
  if [[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" == '1' ]]; then
    booted=true
    break
  fi
  sleep 2
done
if [[ "$booted" != true ]]; then
  adb logcat -d -b crash > runtime-evidence/boot-crash.txt || true
  exit 1
fi
python3 ci/android11/run_device.py /tmp/sgm-internal.apk runtime-evidence
