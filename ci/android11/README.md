# Android 11 native runtime diagnostic

This branch contains an internal test, not a new downloadable release. The main
branch and its existing APK are not changed by the test.

The SHA-bound binary patch reconstructs the already signed internal APK from the
existing candidate 004. The reconstructed file must have SHA256
`f1367e331a7cf21057b073f7f61b61e7630a7853c1d96ffc3b09c738cb2875f0`.
No signing key is included. Standard Android package installation remains enabled.

This internal build removes the multiplayer voice-volume call into the absent
MARS plugin. Run 2 reached the original login process but repeatedly threw
`GetMAXVolume` / `PluginBase.GetContext()` from the original audio settings loader.
Original music, sound effects and character dubbing functions are retained.
Actual gameplay requires review of the Android runtime evidence.

Run 4 confirmed original login, original Traditional Chinese character creation,
and recovery of the created character after force-stop/restart. Map initialization
then repeatedly threw in the absent MARS notification provider. This build keeps
the original notification-state function and makes CancelAllNotify/Notify/
NotifyWithImage/NotifyWithBanner local no-ops. The original map, movement, combat
and map-progress save/load required further testing. It uses a new local development
certificate after workspace recovery; the private key is not uploaded.

Run 5 loaded the original 方外之地 scene and confirmed movement through actual
touch input (minimap coordinates changed from 203,24 to 254,11). Combat and
map-progress restoration did not pass. The restart sequence tapped before the
login finished and its final capture remained at the original login screen.

This test changes the retired SDK's six Java network getters to describe the
single local route. The edit is bound to the original DEX SHA, preserves code
item sizes, and repairs the standard DEX checksums; Android signature validation
remains enabled. It addresses per-frame PluginBase.GetContext exceptions.

It also corrects spawned enemy country and faction flags. The original combat
eligibility bytecode rejects the previous all-zero flags. A 27-check regression
with original constants, data constructors, stage table and attack rules accepts
the enemy flags for sheep/deer/training targets and still protects all seven
starter NPCs. Host checks do not establish Android combat. Runtime diagnostics
now record real entity types, attack requests, damage and saved progress. The
report includes Unity Java/C# exceptions as well as Lua exceptions.

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

Run 6 reached login and character creation with no recorded Unity exceptions.
Its last input capture was still loading. This test uses normal Lua print for
world diagnostics and adds periodic/final captures throughout interaction.
Map, combat and save/load for this exact APK must still be reviewed.
