# Android 11 native runtime diagnostic

This branch contains an internal test, not a new downloadable release. The main
branch and its existing APK are not changed by the test.

The SHA-bound 21 MB patch reconstructs the already signed internal APK from the
existing candidate 004. The reconstructed file must have SHA256
`90d0e954c450549c81f9186b01bbfbed7717af4a53e06e2abe7a709b04e71b3d`.
No signing key is included. Standard Android package installation remains enabled.

This internal build removes the multiplayer voice-volume call into the absent
MARS plugin. Run 2 reached the original login process but repeatedly threw
`GetMAXVolume` / `PluginBase.GetContext()` from the original audio settings loader.
Original music, sound effects and character dubbing functions are retained.
The regression is covered by the 43-assertion host integration test; actual
Android login and gameplay still require the current runtime evidence.

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
