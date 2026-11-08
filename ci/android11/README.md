# Android 11 native runtime diagnostic

This branch contains an internal test, not a new downloadable release. The main
branch and its existing APK are not changed by the test.

The SHA-bound 21 MB patch reconstructs the already signed internal APK from the
existing candidate 004. The reconstructed file must have SHA256
`b849c12f19f518655e4efea5941896dd3712c80b0a3c55d3c67a56b033d6bb8d`.
No signing key is included. Standard Android package installation remains enabled.

This internal build removes the multiplayer voice-volume call into the absent
MARS plugin. Run 2 reached the original login process but repeatedly threw
`GetMAXVolume` / `PluginBase.GetContext()` from the original audio settings loader.
Original music, sound effects and character dubbing functions are retained.
The regression is covered by the 43-assertion host integration test; actual
Android login and gameplay still require the current runtime evidence.

Run 4 confirmed original login, original Traditional Chinese character creation,
and recovery of the created character after force-stop/restart. Map initialization
then repeatedly threw in the absent MARS notification provider. This build keeps
the original notification-state function and makes CancelAllNotify/Notify/
NotifyWithImage/NotifyWithBanner local no-ops. The original map, movement, combat
and map-progress save/load are still unverified. It uses a new local development
certificate after workspace recovery; the private key is not uploaded.

The workflow requires KVM and an official Android 11 Google APIs image with its
ARM compatibility layer. It launches the actual Unity activity, blocks only the
game UID's external traffic, and records screenshots and actual device logs.
It publishes evidence to a separate `sgm-android11-evidence-*` branch. A workflow
success or a running game process does **not** establish that gameplay works.
The login, character creation, original map, movement, combat and save/load flow
still require review and verification before a release can be offered.

The next test session publishes captures while the emulator remains alive for
up to 15 minutes. Input is read from `controls.json` on
`sgm-android11-control-<GITHUB_RUN_ID>`. A document must contain the exact run ID,
the next integer sequence, and a list of allowlisted taps, swipes, ASCII test
names, limited key events, waits, capture, restart, or finish operations. No
arbitrary shell commands or supplied file paths are executed. Evidence records
each consumed sequence; failed commands are not replayed. The `gameplay_verified`
field remains false until the actual images and behavior are reviewed.
